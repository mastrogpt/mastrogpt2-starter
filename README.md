# Welcome to `mastrogpt2-starter` 

# PLEASE READ THIS CAREFULLY IF NOT USING `openserverless.dev`

This repository is  an updated starter for the course **Developing Open LLM applications with Apache OpenServerless**, also known as **The MastroGPT course** thar works also on local clusters (http://miniops.me), and custom installations.

Note the UI is improved and slightly different compared to the videos.

Read the follwign notes on:
- using an alternative Ollama, even a local one
- using your OpenServeress instance
- run the environment locally instead of using codespaces.

If you use it locally, either for hosting or development you need docker. We do not provide information how to install, check on `https://www.docker.com`.

## Using a local or alternative Ollama

If you are NOT using an account on `openserverless.dev` but instead a local Ollama or a custom one, execute the `./configure.sh` script to set host, credentials and protocol.

Example:

```
$ ./configure.sh 
$ ./configure.sh 
=== MastroGPT Configuration ===

Enter Ollama Host [default: host.docker.local:11434]: 
Enter Ollama Auth [default: ignore:me]: 
Enter Ollama Proto [default: http]: 

Configuration summary:
  OLLAMA_HOST: host.docker.local:11434
  OLLAMA_AUTH: ignore:me
  OLLAMA_PROTO: http

Apply these settings? [y/N]: y
```

**Be careful that local Ollama are `http` while cloud Ollama are usually `https`**

Once you have ollama you need to pull at least the following as they are used in the examples:

```
ollama pull mxbai-embed-large:latest
ollama pull llama3.1:8b
ollama pull mistral:7b
ollama pull phi4:14b
ollama pull llama3.2-vision:11b
```

## Using a different instance than OpenServerless

You can self host it either [installing by yourself](https://openserverless.apache.org/docs/installation/) in cloud, or install a local instance of OpenServerless (miniops).

You can install quickly a local instance of OpenServerless if you have docker.

You can do this with the following commands:

1. Install `ops`
  On Linux/Mac:  `curl -sL n7s.co/get-ops | bash`
  On Windows: `powershell -c 'iex n7s.co/get-ops-exe

**NOTE** If you use a different instance than `openserverless.dev`, you have to specify it in the login form. If you use a local instance, use `http://miniops.me` (note the `http`). 

## Running the environment it locally

You can clone the repo and start it and use it locally instead of running it in codespace.
However when you open it with codespace **you have to start the devcontainer**

You can also run the tools without VSCode but you have to start `ops ide devcontainer` to use a devcontainer without VSCode.

## If you want to use OpenServerless.dev (no installation required)

You can:
-  Ask for a free development account on `openserverless.dev` courtesy of [Nuvolaris](http://nuvolaris.io). Contact us:
   - on [Linkedin](https://linkedin.com/in/msciab) sending a private message 
   - on [Discord](https://bit.ly/openserverless-discord) (contact **Michele Sciabarra**)
  
## Launch a codespace with this starter

Once you have your openserverless instance,  go to `https://github.com/mastrogpt/` then select the pinned `mastrogpt2-starter` repo (you should already be here):

![](lessons/assets/starter.png)

Now launch the codespace on it:

![](lessons/assets/codespaces.png)

It takes a bit to download images and starts.

Wait until you see the "openserverless icon", then click on the  OpenServerless Icon and finally, click on Login and put your credentials, as follows:

![](lessons/assets/environment.png)

# Overview

You can recognize below the following icons:

![](lessons/assets/icons.png)

On the vertical Activity Bar to the left:

- **Documents** icon
- **Search** icon
- **Tests** icon
- **OpenServerless** icon

In the Testing panel:
- Run Tests
- Run One Test

Now, let's check that everything works.

## Presentation

Open the course slides:

- Click Documents icon
- Open `lessons/0-welcome.md`
- Click on preview icon

You should see the Apache OpenServerless slides.

## Deployment

Deploy the sample code:

- Click on OpenServerless icon then
- Click on Deploy

Deployment should complete with no errors.

## Testing

Run the tests:

- Click on the Tests Icon 
- Run all the tests

All the tests should pass.

**NOTE**: if you don't see any test, it may help to:

- open directly a test file under `tests``
- if you still dont's see the tests, reload the window

# Develoment Mode

Now lets check the development mode and the user interface:

![](lessons/assets/devmode.png)

1. `OpenServerless` icon then `Devel` button
1. Open the forwarding
1. Click on the "world" icon
1. Login into Pinocchio
1.  `pinocchio`/`geppetto`

![](lessons/assets/pinocchio.png)

# Terminal commands

There are actually plenty of other commands available on the command line.

Open a terminal (Menu: `Terminal` | `New Terminal`) then try:

1. Change the password: `ops ai user update pinocchio`
1. Redeploy the login `ops ide deploy mastrogpt/login`

You are ready!




