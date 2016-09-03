#!/bin/env python3
"""

# Todology - Import Schoology Assignments to Todoist

Imports everything from the schoology calendar that matches the following criteria:
1. Started before the first day of the previous month.
  * For example, if today is the Jan 31 2016, then it will import anything that *starts* on or after
    Dec 1 2015.
2. Has not been imported before. (It keeps track in ~/.todology)

You need to specify your Todoist API Token and Schoology Calendar Feed below. You can also specify
which labels to add to imported tasks, along with the project to import them to. (The project and
any labels will be created if they don't already exist.)

It will automagically rate-limit itself to prevent overloading Todoist, and will still leave some
room for other Todoist clients to do stuff too.

I am not responsible for if this causes something bad to happen to you.

"""
import time
import json
import yaml

from functools import wraps
from os import makedirs
from os.path import expanduser, isfile
from datetime import date, datetime
from urllib.request import urlopen
from icalendar import Calendar
from pytodoist import todoist

DEFAULT_CONFIG = {
  'schoology': {
    'calendar': None
  },
  'todoist': {
    'apiToken': None,
    'project': 'Inbox',
    'labels': ['Todology'],
  },
  'storage': '~/.todology',
}

# The names of the files within the config.storage directory.
STORAGE_FILE_NAMES = {
  'imported': 'imported.json',
}

already_imported = None

#
# Helpers
#

def merge(source, destination):
    """
    Deep-Merge two dictionaries.

    Taken from http://stackoverflow.com/a/20666342/1928484.

    >>> a = { 'first' : { 'all_rows' : { 'pass' : 'dog', 'number' : '1' } } }
    >>> b = { 'first' : { 'all_rows' : { 'fail' : 'cat', 'number' : '5' } } }
    >>> merge(b, a) == { 'first' : { 'all_rows' : { 'pass' : 'dog', 'fail' : 'cat', 'number' : '5' } } }
    True
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            merge(value, node)
        else:
            destination[key] = value

    return destination


def rate_limited(max_per_second):
  """
  Decorator that limits a function to being called max_per_second times per second.

  Taken from https://gist.github.com/gregburek/1441055#gistcomment-1294264, but modified to be
  thread-unsafe. (We don't use threads), and for python3.
  """
  min_interval = 1.0 / float(max_per_second)

  def decorate(f):
    last_time_called = 0.0

    @wraps(f)
    def rate_limited(*args, **kwargs):
      nonlocal last_time_called
      elapsed = time.clock() - last_time_called
      wait = min_interval - elapsed
      if wait > 0:
        time.sleep(wait)

      ret = f(*args, **kwargs)
      last_time_called = time.clock()
      return ret

    return rate_limited

  return decorate

#
# Main Stuff
#

def load_imported_uids(path):
  if not isfile(path):
    return []

  f = open(path, 'r')

  try:
    ret = json.load(f)
    if ret is None:
      ret = []
    return ret
  except:
    return []
  finally:
    f.close()


def store_imported_uids(directory, path):
  makedirs(directory, exist_ok=True)
  with open(path, 'w') as f:
    json.dump(already_imported, f)


class Assignment:
  def __init__(self, uid, title, desc, due, url):
    self.uid = uid
    self.title = title
    self.desc = desc
    self.due = due
    self.url = url

  def __repr__(self):
    return 'Assignment(uid={}, title="{}", desc="{}", due={}, url={})'.format(
      self.uid, self.title, self.desc, self.due, self.url
    )


def start_of_last_month():
  today = date.today()
  year = today.year if today.month >= 2 else today.year - 1
  month = today.month - 1 if today.month >= 2 else 12
  return date(year, month, 1)


def get_assignments(cal):
  assignments = []
  for comp in cal.subcomponents:
    if type(comp).__name__ is not 'Event':
      print('WARNING: Unknown event type `{}`. Ignoring.'.format(type(comp).__name__))
      continue
    start = comp['DTSTART'].dt
    if isinstance(start, datetime):
      start = start.date()
    if comp['UID'] in already_imported:
      continue
    if start >= start_of_last_month():
      assignments.append(
        Assignment(comp['UID'], comp['SUMMARY'], comp['DESCRIPTION'], start, comp['URL'])
      )
  return assignments


def get_label(user, name):
  label = user.get_label(name)
  if label is None:
    label = user.add_label(name)
  return label


@rate_limited(0.5)
def todoist_add(user, projectName, labels, assignments):
  project = user.get_project(projectName)
  labels = [get_label(user, label).id for label in labels]

  if project is None:
    project = user.add_project(projectName)

  for assignment in assignments:
    task = project.add_task('[{}]({})'.format(assignment.title, assignment.url))
    task.due_date = str(assignment.due)
    task.date_string = str(assignment.due)
    task.labels = task.labels + labels
    task.update()
    already_imported.append(assignment.uid)


def todoist_login(apiKey, _times=0):
  """
  A workaround for https://github.com/Garee/pytodoist/issues/12
  """
  try:
    return todoist.login_with_api_token(apiKey)
  except KeyError:
    if _times >= 10:
      raise Exception('Unable to login to Todoist. (Got a KeyError 10 times!) Please try again.')
    else:
      # Ignore it and try again
      return todoist_login(apiKey, _times=_times + 1)


def main():
  global already_imported

  with open('config.yml', 'r') as f:
    config = merge(yaml.safe_load(f), DEFAULT_CONFIG.copy())
  if not isinstance(config, dict):
    print("WARNING: Invalid config.yml. Ignoring.")
    config = DEFAULT_CONFIG.copy()
  config['storage'] = expanduser(config['storage'])
  imported_path = '{}/{}'.format(config['storage'], STORAGE_FILE_NAMES['imported'])

  if not isinstance(config['todoist']['apiToken'], str):
    raise Exception('Invalid API Token!')
  if not isinstance(config['schoology']['calendar'], str):
    raise Exception('Invalid Calendar URL!')

  already_imported = load_imported_uids(imported_path)

  user = todoist_login(config['todoist']['apiToken'])

  with urlopen('https://{}'.format(config['schoology']['calendar'].lstrip('webcal://'))) as f:
    cal = Calendar.from_ical(f.read())

  assignments = get_assignments(cal)

  todoist_add(user, config['todoist']['project'], config['todoist']['labels'], assignments)

  store_imported_uids(config['storage'], imported_path)


if __name__ == '__main__':
  main()

