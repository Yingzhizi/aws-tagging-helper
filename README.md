# aws-tagging-helper
Help to add tags to the resources of each stack which help to calculate const, currently only support adding tag to LogGroup

### Usage
```
python tagging.py [region] -key [key list] -value [value list] --dryrun
```

### Example
```
python tagging.py us-west-2 -key Team Env -value Dev build --dryrun
```
This command will help to update all the resources of type `AWS::Log::LogGroup` below to the cloudformation stack which match tags
`{"Key": "Team", "Value": "Dev"}, {"Key":"Env", "Value": "build"}`
