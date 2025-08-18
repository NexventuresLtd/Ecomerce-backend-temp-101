from datetime import datetime

def account_completion_email(name):
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Account Setup Complete | Nex Market</title>
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
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
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
        .highlight-box {{
            background-color: #f8fafc;
            border-left: 4px solid #1e293b; /* slate-800 accent */
            padding: 16px;
            margin: 24px 0;
            border-radius: 6px;
        }}
        .highlight-box p {{
            margin: 0 0 10px 0;
            font-weight: 500;
            color: #1e293b;
        }}
        .highlight-box ul {{
            color: #475569;
            padding-left: 20px;
            margin: 0;
        }}
        .highlight-box li {{
            margin-bottom: 8px;
        }}
        .btn-primary {{
            background-color: #1e293b; /* slate-800 */
            color: #ffffff !important;
            padding: 12px 28px;
            border-radius: 8px;
            text-decoration: none;
            display: inline-block;
            font-weight: 500;
            margin-top: 20px;
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
            <h1>Account Setup Complete 🎉</h1>
            <p>Dear {name},</p>
            <p>
                Thank you for completing your account setup on <strong>Nex Market</strong>, 
                your gateway to global B2B commerce!
            </p>

            <div class="highlight-box">
                <p>Next Steps:</p>
                <ul>
                    <li>Complete email verification for full account security</li>
                    <li>Our team will review your account details within 24 hours</li>
                    <li>Start exploring our marketplace features</li>
                </ul>
            </div>

            <p>
                <strong>Important:</strong> Accounts with inaccurate information may be suspended 
                to maintain marketplace integrity.
            </p>
            <p>
                Your account is now active and ready for limited use while under review.
            </p>

            <a href="https://nexventures.net/dashboard" class="btn-primary">Go to Your Dashboard</a>
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
