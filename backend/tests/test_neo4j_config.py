"""Tests for Neo4j target profile resolution."""

import os
from unittest.mock import patch

import pytest

from database.config import Neo4jSettings, _aura_uri_from_instance_id


def test_hosted_rejects_local_default_password():
    env = {
        "NEO4J_TARGET": "hosted",
        "NEO4J_HOSTED_URI": "neo4j+s://x.databases.neo4j.io",
        "NEO4J_HOSTED_PASSWORD": "password",
    }
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ValueError, match="local default password"):
            Neo4jSettings()


def test_hosted_target_custom_uri():
    env = {
        "NEO4J_TARGET": "hosted",
        "NEO4J_HOSTED_URI": "neo4j+s://my.db.host:7687",
        "NEO4J_HOSTED_PASSWORD": "secret",
    }
    with patch.dict(os.environ, env, clear=True):
        settings = Neo4jSettings()
    assert settings.uri == "neo4j+s://my.db.host:7687"


def test_local_target_defaults_to_localhost():
    with patch.dict(os.environ, {"NEO4J_TARGET": "local"}, clear=True):
        with patch("database.config._is_docker_environment", return_value=False):
            settings = Neo4jSettings()
    assert settings.uri == "bolt://localhost:7687"
