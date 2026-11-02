from dify_plugin import DifyPluginEnv, Plugin

# Crawls report progress while they run, so allow longer calls than the default.
plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=900))

if __name__ == "__main__":
    plugin.run()
