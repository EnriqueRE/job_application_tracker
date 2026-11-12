# No authentication; access is controlled by the network

The tracker has a single user and runs in Docker on that user's own machine. It is reached only through localhost or the user's private Tailscale tailnet, so the application has no login, sessions or user accounts. Network membership is the access control. The app must never be exposed on a public interface or through a public tunnel without first adding authentication, which would supersede this ADR.
