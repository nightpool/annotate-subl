
require 'sinatra'
require 'rest-client'

helpers do 
    def payload(code)
        {
          "code": code,
          "client_id": ENV['client_id'],
          "client_secret": ENV['client_secret'],
          "redirect_uri": ENV['redirect_uri'],
          "response_type": "code",
          "grant_type": "authorization_code"
        }
    end

    def get_token(code)
        RestClient.post "#{ENV['api_path']}/oauth/token", payload(code), :accept => :json
    end

    def install
        <<-EOF
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
    end
end

get '/auth' do
    code = params[:code]
    erb install, locals: {token: get_token(code)}
end

set :server, "webrick"