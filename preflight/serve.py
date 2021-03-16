import cli

@cli.preflight_plugin("serve",
                      [cli.Argument("--port", "-p", type=int, default=8000)])
def serve(container, options):
    container.add_port(options.port)
