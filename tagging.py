# python tagging.py [key] [name] --dry-run

import boto3
import re
import sys
import argparse
import logging
import json
from abc import ABC, abstractmethod

FORMATTER = logging.Formatter('%(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S')

def get_stream_handler():
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(FORMATTER)
    stream_handler.setLevel(logging.INFO)
    return stream_handler

def get_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.addHandler(get_stream_handler())
    return logger

logger = get_logger('root')

class TagGenerater(ABC):
    @abstractmethod
    def tag_resource(self, resources, tags):
        pass

class TagLogGroup(TagGenerater):
    def __init__(self, region):
        self.client = boto3.client('logs', region_name=region)

    def tag_resource(self, resource, tags, dry_run):
        # reformat tags
        applied_tags = {}
        for tag in tags:
            if not re.match(r'^aws', tag["Key"]):
                applied_tags[tag["Key"]] = tag["Value"]
        # tag log group
        if "AWS::Logs::LogGroup" in resource.resource_type:
            log_group_name = resource.physical_resource_id
            log_group_type = resource.resource_type
            response = self.client.list_tags_log_group(logGroupName=log_group_name)['tags']

            if response != applied_tags:
                # if no tag before, add tags to log group, otherwise, update
                if response == {}:
                    logger.info('  Add tag {} for loggroup of {}'.format(applied_tags, log_group_name))
                else:
                    logger.info('  Update tag from {} to {} for loggroup of {}'.format(response, applied_tags, log_group_name))
                if not dry_run:
                    self.client.tag_log_group(logGroupName=log_group_name, tags=applied_tags)
            else:
                logger.info('  {} already has tag {}, no update needed'.format(log_group_name, response))

class Processor(object):
    def __init__(self, tag_generater, cfn_resource, tags):
        self.tag_generater = tag_generater
        self.cfn_resource = cfn_resource
        self.tags = tags

    def match_tags(self, stack_tags):
        stack_tag_dict = {}
        for tag in stack_tags:
            stack_tag_dict[tag["Key"]] = tag["Value"]
        for key, value in self.tags.items():
            if key in stack_tag_dict and value == stack_tag_dict[key]:
                continue
            else:
                return False
        return True

    def filter_stacks(self):
        filter_stacks = []
        for stack in self.cfn_resource.stacks.all():
            if self.match_tags(stack.tags):
                filter_stacks.append(stack)
        return filter_stacks

    def run(self, dry_run):
        if dry_run:
            logger.info("Dry run.....")
        else:
            logger.info("Start tagging......")

        filter_stacks = self.filter_stacks()
        if len(filter_stacks) == 0:
            logger.info("Cannot find any stacks has tags {}, skip tagging".format(self.tags))
            return
        for stack in self.filter_stacks():
            logger.info("[Stack: {}]".format(stack.stack_name))
            for resource in stack.resource_summaries.all():
                self.tag_generater.tag_resource(resource, stack.tags, dry_run)
        logger.info("\nComplete Updating")
  
if __name__== "__main__":
    # set up parser
    parser = argparse.ArgumentParser()
    parser.add_argument("region", help="AWS region")
    parser.add_argument('-key', nargs='+', help='The list of tag key, e.g. -k "Team" "Env"', required=True)
    parser.add_argument('-value', nargs='+', help='The list of tag value, e.g. -k "Data Architecture" "build"', required=True)
    parser.add_argument("--dryrun", help="Optional, For testing purpose", action="store_true")
    args = parser.parse_args()

    # init client
    cfn_resource = boto3.resource('cloudformation', region_name=args.region)

    # here generate class taglogGroup, if has futher need it, can add it depends on args.method
    tag_generater = TagLogGroup(args.region)

    tags = dict(zip(args.key, args.value))
    logger.info("Start looking for stacks matching tag {} in {}...".format(tags, args.region))
    p = Processor(tag_generater, cfn_resource, tags)

    p.run(args.dryrun)