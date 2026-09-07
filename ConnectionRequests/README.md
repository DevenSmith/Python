# Mock connection requests

Run the tests from this directory:

```powershell
python -m unittest -v
```

The domain exceptions expose the intended HTTP response status through their
`status_code` attribute. An HTTP framework adapter can translate these errors
to JSON responses without coupling the service to a specific framework.
