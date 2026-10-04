"""Vercel Python function using the same handler as the local API."""
from api_server import LifeMapAPIHandler


class handler(LifeMapAPIHandler):
    pass
