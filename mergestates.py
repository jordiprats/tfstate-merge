import tempfile
import json
import sys
import os

DEBUG = os.getenv("DEBUG", False)
DRYRUN = os.getenv("DRYRUN", False)

def run(dir, command):
  if DEBUG:
    print(command)
  if not DRYRUN:
    exit_code = os.system("cd "+dir+"; "+command)
    return exit_code
  else:
    return 0

if len(sys.argv) <= 2 :
  sys.exit("Usage: "+ sys.argv[0] + " <project1> <project2> ... <target_project>")

for project in sys.argv[1:]:
  # check if directory exists
  if not os.path.isdir(project):
    sys.exit("Directory " + project + " does not exist")

try:
  tmpdir = tempfile.mkdtemp()
  if DEBUG:
    print("tmpdir: " + tmpdir)

  projects = []
  i=0
  for project in sys.argv[1:-1]:
    projects.append({'name': str(i),'path': project, "tmpfile": tmpdir+"/"+str(i)})
    i+=1

  if DEBUG:
    print("projects:")
    for project in projects:
      print("  " + project['path'])

  target_project = sys.argv[-1]
  if DEBUG:
    print("target: " + sys.argv[-1])

  # target terraform state
  if run(target_project, "terraform state pull  > " + tmpdir+'/target'):
    sys.exit("Error retrieving terraform state for " + project['path'])

  # load json target state
  target_state = json.load(open(tmpdir+'/target'))

  # retrieve terraform states
  for project in projects:
    if run(project['path'], "terraform state pull  > " + project['tmpfile']):
      sys.exit("Error retrieving terraform state for " + project['path'])
    else:
      # load json state
      state = json.load(open(project['tmpfile']))

      # merge resources
      target_state['resources'] = state['resources'] + target_state['resources']

  # increment serial
  target_state['serial'] = target_state['serial'] + 1

  # write merged state
  with open(tmpdir+'/merged', 'w') as outfile:
    json.dump(target_state, outfile)

  if run(target_project, "terraform state push  " + tmpdir+'/merged'):
      sys.exit("Error pushing terraform state to " + target_project)

except Exception as e:
  print("Error: " + str(e))
  sys.exit(1)

finally:
  if not DRYRUN:
    # remove tmpdir
    if tmpdir and os.path.isdir(tmpdir):
      if DEBUG:
        print("removing tmpdir: " + tmpdir)
      # os.system("rm -rf " + tmpdir)