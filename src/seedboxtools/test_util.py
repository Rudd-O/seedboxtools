import seedboxtools.util as m

def test_which():
   # Should be true on most Unices.
   assert m.which("true").endswith("true")
   assert m.which("narostnaironstio") == None
