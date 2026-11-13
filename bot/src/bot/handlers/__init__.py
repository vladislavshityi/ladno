from bot.handlers import fallback, issues, start

routers = [start.router, issues.router, fallback.router]
