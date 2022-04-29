import tempfile
import json
import sys
import os

DEBUG = os.getenv("DEBUG", False)
DRYRUN = os.getenv("DRYRUN", False)

def run(dir, command):
  if DEBUG:
    print(command)
  return os.system("cd "+dir+"; "+command)

def exists_resource(resource, resources):
  for item in resources:
    # "mode":"data",
    # "type":"aws_route53_zone",
    # "name":"private",
    if item["mode"] == resource["mode"] and item["type"] == resource["type"] and item["name"] == resource["name"]:
      if DEBUG:
        print("FOUND " + resource['mode'] + " " + resource['type'] + " " + resource['name'])
      return True
  return False

###############################################################################

if len(sys.argv) <= 2 :
  sys.exit("Usage: "+ sys.argv[0] + " <project1> <project2> ... <target_project>")

for project in sys.argv[1:]:
  # check if directory exists
  args = project.split(':')
  if len(args) == 1:
    if not os.path.isdir(project):
      sys.exit("Directory " + project + " does not exist")
  else:
    if not os.path.isdir(args[0]):
      sys.exit("Directory " + args[0] + " within "+ project + " does not exist")

try:
  tmpdir = tempfile.mkdtemp()
  if DEBUG:
    print("tmpdir: " + tmpdir)

  projects = []
  i=0
  for project in sys.argv[1:-1]:
    args = project.split(':')
    if len(args) == 1:
      projects.append({'name': str(i),'path': project, "tmpfile": tmpdir+"/"+str(i)})
    else:
      projects.append({'name': str(i),'path': args[0], "tmpfile": tmpdir+"/"+str(i), "item": args[1]})
    i+=1

  if DEBUG:
    print("projects:")
    for project in projects:
      print("  " + project['path'])
      if "item" in project.keys():
        print("    item: " + project["item"])

  target_project = sys.argv[-1]
  if DEBUG:
    print("target: " + sys.argv[-1])

  # target terraform state
  if run(target_project, "terraform state pull  > " + tmpdir+'/target'):
    sys.exit("Error retrieving terraform state for " + project['path'])

  # load json target state
  try:
    target_state = json.load(open(tmpdir+'/target'))
  except:
    sys.exit("Error loading target's terraform state")

  # retrieve terraform states
  for project in projects:
    if run(project['path'], "terraform state pull  > " + project['tmpfile']):
      sys.exit("Error retrieving terraform state for " + project['path'])
    else:
      # load json state
      try:
        state = json.load(open(project['tmpfile']))
      except:
        sys.exit("Error loading terraform state for: " + project['path'])

      # merge all resources
      if "item" not in project.keys():
        resources = state['resources']

        for resource in target_state['resources']:
          # merge data resources skipping source resources
          if resource["mode"] == "data" and exists_resource(resource, resources):
            if DEBUG:
              print("      " + resource['type'] + "/" + resource['name'] + " exists in target state")
            try:
              resources.remove(resource)
            except:
              if DEBUG:
                print("      skipping "+ resource['mode'] + "." + resource['type'] + "." + resource['name'])
              pass

        # print(str(resources))

      else:
        # merge specific resource
        resources = []

        for resource in state['resources']:
          # {'module': 'module.spinnaker-service.module.rosco.module.kms-parameter-store[0]', 'mode': 'managed', 'type': 'aws_iam_role_policy_attachment', 'name': 'ssm_role_policy_attachment',
          base = ''
          if 'module' in resource.keys():
            base = resource['module'] + '.'

          if resource['mode'] == 'data':
            resource_path = base+resource['mode']+'.'+resource['type']+'.'+resource['name']
          else:
            resource_path = base+resource['type']+'.'+resource['name']

          if resource_path == project['item']:
            if resource["mode"] == "data" and exists_resource(resource, target_state['resources']):
              if DEBUG:
                print("      skipping " + resource_path + " Already exists in target state")
            else:
              if DEBUG:
                print(">> adding " + resource_path)
              resources.append(resource)

      if DEBUG and len(resources) == 0:
        print("      no-op merge for " + project['path'])

      # merge resources into target state
      target_state['resources'] = resources + target_state['resources']

  # increment serial
  target_state['serial'] = target_state['serial'] + 1

  # write merged state
  with open(tmpdir+'/merged', 'w') as outfile:
    json.dump(target_state, outfile)

  if not DRYRUN:
    if run(target_project, "terraform state push  " + tmpdir+'/merged'):
        sys.exit("Error pushing terraform state to " + target_project)
  else:
    print("DRYRUN - skipping: terraform state push")

except Exception as e:
  if DEBUG:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno)
  print("Error: " + str(e))
  sys.exit(1)

finally:
  if not DRYRUN:
    # remove tmpdir
    if tmpdir and os.path.isdir(tmpdir):
      if DEBUG:
        print("removing tmpdir: " + tmpdir)
      os.system("rm -rf " + tmpdir)
  else:
    print("not removing temporal files: " + tmpdir)