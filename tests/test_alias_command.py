# pylint: disable=c0114,c0116

from clickext import AliasCommand


def test_alias_order():
    cmd = AliasCommand(["c", "a", "b"], "cmd")
    assert ["a", "b", "c"] == cmd.aliases


def test_help_name():
    cmd = AliasCommand(["c", "a", "b"], "cmd")
    assert cmd.name_for_help == "cmd (a,b,c)"
