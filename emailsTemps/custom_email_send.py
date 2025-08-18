from datetime import datetime

def custom_email(name, heading, msg):
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nex Market</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
        body {{
            font-family: 'Inter', Arial, sans-serif;
            background-color: #f1f5f9;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background: #ffffff;
            border-radius: 12px;
            overflow: hidden;
        }}
        .header {{
            background-color: #1e293b; /* slate-800 */
            padding: 24px;
            text-align: center;
        }}
        .header img {{
            max-width: 160px;
        }}
        .content {{
            padding: 40px 32px;
            color: #334155;
        }}
        .content h1 {{
            font-size: 24px;
            font-weight: 600;
            color: #1e293b;
            margin-top: 0;
        }}
        .content p {{
            font-size: 15px;
            line-height: 1.6;
            margin: 16px 0;
            color: #475569;
        }}
        .btn-primary {{
            background-color: #1e293b; /* slate-800 */
            color: #ffffff !important;
            padding: 12px 28px;
            border-radius: 8px;
            text-decoration: none;
            display: inline-block;
            font-weight: 500;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            padding: 24px;
            font-size: 13px;
            color: #64748b;
            background: #f8fafc;
        }}
        .footer a {{
            color: #1e293b;
            text-decoration: none;
            margin: 0 6px;
            font-weight: 500;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <img src="https://www.nexventures.net/icon.png" alt="Nex Market" />
        </div>

        <!-- Content -->
        <div class="content">
            <h1>{heading}</h1>
            <p>Dear {name},</p>
            <p>{msg}</p>
            
            <p style="font-size: 14px; color: #64748b; margin-top: 24px;">
                Need help? Contact our support team at 
                <a href="mailto:support@nexventures.net" style="color: #1e293b;">support@nexventures.net</a>
            </p>
        </div>

        <!-- Footer -->
        <div class="footer">
            <p>&copy; {datetime.now().year} Nex Market. All rights reserved.</p>
            <p>
                <a href="https://nexventures.net">Our Website</a> • 
                <a href="https://nexventures.net/privacy">Privacy Policy</a> • 
                <a href="https://nexventures.net/terms">Terms of Service</a>
            </p>
            <p>Nex Ventures Ltd, International Business Center</p>
        </div>
    </div>
</body>
</html>
"""
