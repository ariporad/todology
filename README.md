# Todology
### Import Schoology Assignments to Todoist

I was sick of manually copying my assignments from Schoology to Todoist. So I made a script to do it
for me.

***DISCLAIMER:** I am not responsible if this script causes something bad for you. If your school IT
person has something against scripts and gets you expelled for using this one, I am not responsible.
If for some reason it drops an assignment and you turn it in late, I am not responsible. (Although
it shouldn't do that, and I do use it myself.) You should still double-check schoology.*

## Usage

First, clone this repo:

```bash
$ git clone git@github.com:ariporad/todology
$ cd todology
```

Then, install the dependencies. (You'll need Python 3 for this. You should probably use virtualenv
too.):

```bash
$ pip install -r requirements.txt
```

Next, copy the `config.sample.yml` to `config.yml`, and edit it. (There are helpful
comments to guide you through the process.):

```bash
$ cat config.sample.yml > config.yml
$ vim config.yml
```

Finally, run it:

```bash
python3 index.py
```

You should run it whenever you want to import events to Todoist. It will automagically not import
the same event multiple times. (*NOTE:* It stores the information about already-imported events on
your computer. If you run it on different computers, it will probably do something bad.)

## How it Works (Nerdy Details)

This script works by downloading the Schoology calendar feed, and parsing it. It then converts
calendar events into a list of assignments that need to be imported. It imports any event which
matches the following criteria:
1. The start date is before the 1st of the previous month.
  * For example, if today is the Jan 31 2016, then it will import anything that *starts* on or after
    Dec 1 2015.
2. And has not been imported before. (By default, it keeps track of this in `~/.todology`)

Then, it takes the list of assignments and imports them all in to Todoist using their fantastic API.

## License

[The MIT License.](https://ariporad.mit-license.org)

I am not responsible for any damage this may cause. Use at your own risk.
