#!/usr/local/ruby/bin/ruby

client_secret = File.open('client-secret').read.strip

require 'sinatra'
require 'rest-client'

client_id = "ciUq7-YBs7OvIBqyEbX6CTMFwBzxXfC_0bMmMPsXfLWopNHyVm3ZfCTpyDtuSj6n"
redirect_uri = "http://nightpool.me/annotate-subl-auth"
api_path = "https://api.genius.com"

helpers do 
    def payload(code)
        {
          "code": code,
          "client_id": client_id,
          "client_secret": client_secret,
          "redirect_uri": redirect_uri,
          "response_type": "code",
          "grant_type": "authorization_code"
        }
    end

    def get_token(code)
        RestClient.post "#{api_path}/oauth/token", payload(code), :accept => :json
    end
end

get '/auth' do
    code = params[:code]
    erb install, locals: {token: get_token(code)}
end

install = <<EOF
<!DOCTYPE html>
<html>
<head>
    <title>Annotate Sublime Installation</title>
    <style type="text/css">
        
    </style>
</head>
<body>

<h1>Authorization Successful</h1>

<p>Copy the following code and paste it into Sublime:</p>

<textarea readonly="true" onclick="this.select();this.setSelectionRange(0, 9999);"><%= token %></textarea>

</body>
</html>
EOF

# set :server, "CGI"