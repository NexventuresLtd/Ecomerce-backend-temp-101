from enum import Enum
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from Endpoints.Auth import auth ,verification, resetPassword ,refreshToken
from Endpoints.two_factor import otp
from fastapi.responses import HTMLResponse
# from db.database import Base,engine
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer_scheme = HTTPBearer()
app = FastAPI(
    title="Nex Market - Global B2B Marketplace API",
    description="""
    Nex Market is a global B2B marketplace connecting vendors and buyers worldwide. 
    Our platform provides seamless trade solutions with secure transactions, 
    vendor management, and real-time communication tools.
    """,
    version="1.0.0",
    contact={
        "name": "Nex Market Support",
        "email": "support@nexventures.net",
    },
    license_info={
        "name": "Proprietary",
    },
)



# Configure CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(refreshToken.router)
app.include_router(resetPassword.router)
app.include_router(verification.router)
app.include_router(auth.router)
app.include_router(otp.router)
@app.get("/secure-data")
def secure_data(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    # Here you can verify token however you want
    return {"message": "Access granted", "token_used": token}
@app.get("/", response_class=HTMLResponse)
async def read_root():
    html_content = f"""
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nex Market | Global B2B Marketplace</title>
    <!-- Tailwind CSS -->
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <style>
        .bg-slate-800 {{
            background-color: #1e293b;
        }}
        .gradient-text {{
            background: linear-gradient(90deg, #3b82f6, #10b981);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }}
    </style>
</head>

<body class="bg-slate-800 text-gray-100">
    <div class="container mx-auto py-12 px-4">
        <header class="text-center mb-12">
            <h1 class="text-5xl font-bold mb-4 gradient-text">Nex Market</h1>
            <p class="text-xl text-gray-300">The Global B2B Marketplace Connecting Vendors and Buyers Worldwide</p>
        </header>

        <section class="max-w-4xl mx-auto bg-gray-900 bg-opacity-50 backdrop-blur-sm rounded-xl p-8 shadow-2xl border border-gray-700">
            <div class="flex flex-col md:flex-row gap-8">
                <div class="md:w-2/3">
                    <h2 class="text-2xl font-bold text-white mb-4">API Documentation</h2>
                    <p class="text-gray-300 mb-6">
                        Nex Market provides a comprehensive API for integrating with our global B2B marketplace platform.
                        Our API enables seamless vendor management, product listings, order processing, and secure transactions.
                    </p>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                        <div class="bg-gray-800 p-4 rounded-lg border-l-4 border-blue-500">
                            <h3 class="font-bold text-white mb-2">Vendor Services</h3>
                            <p class="text-gray-400 text-sm">Manage product listings, inventory, and orders</p>
                        </div>
                        <div class="bg-gray-800 p-4 rounded-lg border-l-4 border-green-500">
                            <h3 class="font-bold text-white mb-2">Buyer Services</h3>
                            <p class="text-gray-400 text-sm">Browse products, place orders, and track shipments</p>
                        </div>
                        <div class="bg-gray-800 p-4 rounded-lg border-l-4 border-red-500">
                            <h3 class="font-bold text-white mb-2">Agent Services</h3>
                            <p class="text-gray-400 text-sm">Middleman who helps buyers & sellers connect.</p>
                        </div>
                        <div class="bg-gray-800 p-4 rounded-lg border-l-4 border-yellow-500">
                            <h3 class="font-bold text-white mb-2">Admin / Platform Manager</h3>
                            <p class="text-gray-400 text-sm">Manage entire ecosystem, ensure security & compliance.</p>
                        </div>
                    </div>
                </div>
                
                <div class="md:w-1/3 flex flex-col justify-center">
                    <div class="space-y-4">
                        <a href="/docs" class="block w-full text-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-lg transition duration-300 font-medium">
                            Interactive Docs
                        </a>
                        <a href="/redoc" class="block w-full text-center px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg shadow-lg transition duration-300 font-medium">
                            ReDoc Documentation
                        </a>
                        <a href="#" class="block w-full text-center px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg shadow-lg transition duration-300 font-medium">
                            API Status
                        </a>
                    </div>
                </div>
            </div>
            
            <div class="mt-8 pt-6 border-t border-gray-700">
                <h3 class="text-lg font-semibold text-white mb-4">Platform Features</h3>
                <ul class="grid grid-cols-1 md:grid-cols-3 gap-4 text-gray-300">
                    <li class="flex items-start">
                        <svg class="h-5 w-5 text-green-500 mr-2 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                        Secure Transactions
                    </li>
                    <li class="flex items-start">
                        <svg class="h-5 w-5 text-green-500 mr-2 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                        Global Vendor Network
                    </li>
                    <li class="flex items-start">
                        <svg class="h-5 w-5 text-green-500 mr-2 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                        Real-time Analytics
                    </li>
                    <li class="flex items-start">
                        <svg class="h-5 w-5 text-green-500 mr-2 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                        Multi-language Support
                    </li>
                    <li class="flex items-start">
                        <svg class="h-5 w-5 text-green-500 mr-2 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                        Escrow Payment System
                    </li>
                    <li class="flex items-start">
                        <svg class="h-5 w-5 text-green-500 mr-2 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                        Logistics Integration
                    </li>
                </ul>
            </div>
        </section>
        
        <footer class="mt-12 text-center text-gray-400 text-sm">
            <p>© 2025 Nexventures Ltd. All rights reserved.</p>
            <p class="mt-2">Connecting global buyers and suppliers since 2025</p>
        </footer>
    </div>
</body>

</html>
    """
    return HTMLResponse(content=html_content)