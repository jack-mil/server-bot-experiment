# Image-Frame Discord Bot
This is a rudimentary proof-of-concept experiment that uses the Discord bot API to connect
a Discord client "user" and a remote "server" (such as RPI with display) over the internet
without additional networking.

The server runs two Docker containers:
- A Flask server listening to REST API requests on the local network (`127.0.0.1`)
- The Discord bot, which can pass data back/forth to the outside world over the internet
  - The bot forwards API requests to the local web server

With this setup, it is possible to send commands, data, or whole files to the "server" from 
the Discord mobile app with no network configuration.
As long as the client and server both haver internet access.
The Discord bot can forward data on to the local web server,
which can save or process the data as needed. 

*One application for this is a live "picture frame" where users can message images to the 
bot to be displayed on the RPI device (running a browser in kiosk mode).* Images can be
 hosted on the Discord CDN or downloaded to the server directly.

The current proof-of-concept shows that a webpage displayed on the Pi can be updated
asynchronously with images sent to the Discord bot using the Server-Sent-Events browser 
feature to update the web page with images in a "feed" style.

An exercise in specific learning areas:
 - Making Flask REST-like APIs
 - Asynchronous programming with `discord.py`
 - Containerization with Docker Compose
 - Browser support of Server-Sent-Events (SSE) and dynamic page updating
   - Some client side Javascript required in the web page hosted by the local server


### Attribution

The [EM Felix Bot](https://github.com/engineer-man/felix) served as a great foundation for a modular bot structure.
Parts of code where copied from there, before being modified and features removed for my experimental purposes.
Code from that project is used under the MIT License. [Felix License](https://github.com/engineer-man/felix/blob/1c635ed909ce98b1c446f371dffde265351f4021/LICENSE)
