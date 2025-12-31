package main

import (
    "testgin/config"
    "testgin/routers"
)

func main() {
    config.InitConfig()
    r := routers.InitRouter()
    r.Run(config.AppConfig.Server.Port)
}
