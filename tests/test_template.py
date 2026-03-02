import pytest
from jinja2.exceptions import TemplateNotFound
from src.template import load_template


@pytest.fixture
def template_file(tmp_path):
    template = tmp_path / "template.conf.j2"
    template.touch()
    return template


def test_load_template(tmp_path, template_file):
    with pytest.raises(TemplateNotFound):
        load_template(tmp_path / "nonexistent.conf.j2")

    template = load_template(template_file)
    assert template.render() == ''
