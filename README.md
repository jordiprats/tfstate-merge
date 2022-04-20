# tfstate-merge

Merge resources from several terraform states into another one

## Usage

We can merge resources from any project to any other project, it doesn't really matter what backend you are using:

```
python mergestates.py /home/jprats/terraform/projectA /home/jprats/terraform/projectB ... /home/jprats/terraform/projectZ
```

DEBUG = os.getenv("DEBUG", False)
DRYRUN = os.getenv("DRYRUN", False)