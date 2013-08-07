from saltcli.commands import Command

class Empty(Command):
  def __init__(self, environment):
    super(Empty, self).__init__(environment)

  def run(self):
    import saltcli.utils.template
    for name, inst in self.environment.instances.items():
      script = saltcli.utils.template.gen_rendered_script(inst, {})
      with open(script, 'r') as fp:
        print fp.read()

    # template = 
    # copyfile
    # _render_script('')