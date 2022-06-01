import seedboxtools.util as m

def test_which():
   # Should be true on most Unices.
   assert m.which("true") == "/bin/true"
   assert m.which("narostnaironstio") == None
