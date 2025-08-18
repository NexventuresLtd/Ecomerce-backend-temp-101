def _verification_template(title: str, message: str, button_text: str, icon: str, color: str) -> str:
    """Reusable Tailwind template for verification responses."""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <script src="https://cdn.tailwindcss.com"></script>
        <title>{title}</title>
    </head>
    <body class="bg-slate-100 flex items-center justify-center min-h-screen font-sans">
        <div class="bg-white p-10 rounded-2xl shadow-xl text-center max-w-lg w-full border border-slate-200">
            <div class="flex justify-center mb-6">
                <span class="text-6xl {color}">{icon}</span>
            </div>
            <h1 class="text-3xl font-bold text-slate-800 mb-4">{title}</h1>
            <p class="text-gray-600 mb-8">{message}</p>
            <a href="http://localhost:5174/" 
               class="inline-block px-8 py-3 rounded-xl bg-slate-800 text-white font-medium shadow hover:bg-slate-700 hover:scale-105 transform transition">
                {button_text}
            </a>
        </div>
    </body>
    </html>
    """
