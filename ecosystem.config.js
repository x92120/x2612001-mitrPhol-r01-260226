module.exports = {
    apps: [
        {
            name: "mqtt-bridge",
            script: "./x09-LocalMqtt/x01-ScaleRead/mqtt_bridge.py",
            interpreter: "python3",
            watch: false,
            autorestart: true,
            restart_delay: 5000,
            env: {
                PYTHONUNBUFFERED: "1"
            }
        },
        {
            name: "mixing-frontend",
            cwd: "./x01-FrontEnd/x0101-xMixing_Nuxt",
            script: "npm",
            args: "run dev",
            watch: false,
            autorestart: true,
            restart_delay: 5000,
            env: {
                PORT: 3000,
                NODE_ENV: "development"
            }
        }
    ]
};
