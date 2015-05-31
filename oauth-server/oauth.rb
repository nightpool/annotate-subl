
require 'sinatra'
require 'rest-client'

error do
  'Sorry there was a nasty error - ' + env['sinatra.error'].message
end

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
        resp = RestClient.post "#{ENV['api_path']}/oauth/token", payload(code), :accept => :json
        JSON.parse(resp)["access_token"]
    end

    def install
        <<-EOF
            <!DOCTYPE html>
            <html>
            <head>
                <title>Annotate Sublime Installation</title>
                <style type="text/css">
                    @import url(http://fonts.googleapis.com/css?family=Open+Sans:400,700);
                    body {
                      max-width: 900px;
                      margin: auto;
                      text-align: center;
                    }
                    * {
                        font-family: 'Open Sans', sans-serif;
                    }
                    h1 {
                      font-size: 3em;
                      font-weight: bold;
                      letter-spacing: 7px;
                      margin-bottom: 0;
                    }
                    p  {
                      font-size: 1.8em;
                      margin: .5em auto 1.5em auto;
                      color: #a5a5a5;
                    }
                    textarea {
                      font-size: 1.4em;
                      width: 100%;
                      background: #aaa;
                      color: #505050;
                      text-align: center;
                      resize: none;
                      cursor: text;
                      padding: 1em;
                      line-height: 0;
                      vertical-align: middle;
                      border: 1px solid black;
                    }
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