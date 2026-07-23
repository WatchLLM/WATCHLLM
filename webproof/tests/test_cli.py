import json

import responses

from watchllm_webproof.cli import main


@responses.activate
def test_cli_prints_json_proof(tmp_path, capsys):
    config = tmp_path / "config.yaml"
    config.write_text("version: 1\n")
    responses.add(responses.GET, "https://example.com/", status=200)
    assert main(["verify-url", "https://example.com/", "--config", str(config)]) == 0
    proof = json.loads(capsys.readouterr().out)
    assert proof["leaf_count"] == 1
    assert proof["proof_type"] == "local_merkle_stub"


def test_cli_sensible_error(tmp_path, capsys):
    config = tmp_path / "config.yaml"
    config.write_text("version: 1\n")
    assert main(["verify-url", "ftp://example.com/", "--config", str(config)]) == 1
    assert "HTTP and HTTPS only" in capsys.readouterr().err
