from jinja2 import Template
import tempfile, shutil, os

def _render_script(path, opts={}):
  '''
    Return a rendered script
  '''
  print path
  try:
    with open(path, 'r') as fp:
      template = Template(fp.read())
      return str(template.render(opts=opts))
  except:
    with open(path, 'r') as fp:
      return fp.read()

def _get_script(instance):
  this_dir = os.path.dirname(os.path.realpath(__file__))
  bootstrap_dir = os.path.join(this_dir, "..", "..", "bootstrap")

  if instance.ismaster():
    script_name = "master.sh"
  else:
    script_name = "minion.sh"
  return os.path.join(bootstrap_dir, script_name)

def write_to_tempfile(contents):
  '''
  Write the contents into a tempfile
  '''
  temp = tempfile.NamedTemporaryFile(delete=False)
  temp.write(contents)
  temp.flush()
  return temp

def gen_rendered_script(instance, opts={}):
  script = _get_script(instance)
  rendered = _render_script(script, opts)

  return write_to_tempfile(rendered)
