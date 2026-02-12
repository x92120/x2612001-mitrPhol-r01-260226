const COMMON_CONFIG = {
    watch: false,
    autorestart: true,
    restart_delay: 5000,
};

module.exports = {
    apps: [
        {
            ...COMMON_CONFIG,
            name: "mqtt-bridge",
            script: "./x09-LocalMqtt/x01-ScaleRead/mqtt_bridge.py",
            interpreter: "python3",
            env_production: { PYTHONUNBUFFERED: "1", NODE_ENV: "production" },
            env_development: { PYTHONUNBUFFERED: "1", NODE_ENV: "development", watch: true }
        },
        {
            ...COMMON_CONFIG,
            name: "mixing-frontend",
            cwd: "./x01-FrontEnd/x0101-xMixing_Nuxt",
            script: "npm",
            args: "run dev",
            env_production: { PORT: 3000, NODE_ENV: "production" },
            env_development: { PORT: 3000, NODE_ENV: "development" }
        },
        {
            ...COMMON_CONFIG,
            name: "mixing-backend",
            cwd: "./x02-BackEnd/x0201-fastAPI",
            script: "main.py",
            interpreter: "/Users/x92120/x2612001-mitrPhol/x02-BackEnd/.venv/bin/python3",
            env_production: { PORT: 8001, PYTHONUNBUFFERED: "1", NODE_ENV: "production" },
            env_development: { PORT: 8001, PYTHONUNBUFFERED: "1", NODE_ENV: "development" }
        }
    ]
};
