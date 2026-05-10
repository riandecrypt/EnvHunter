# EnvHunter
EnvHunter adalah tool security testing untuk mendeteksi dan mengekstrak public environment variables yang terekspos pada aplikasi modern berbasis Next.js, Vite, React, dan Nuxt.js. Tool ini membantu developer dan security researcher mengidentifikasi potensi kebocoran informasi sensitif di frontend applications.

📌 Fitur Utama

    ✅ Multi-Framework Support - Mendeteksi variables dari Next.js (NEXT_PUBLIC_*), Vite (VITE_*), React (REACT_APP_*), Nuxt.js (NUXT_PUBLIC_*)

    ✅ Automatic JS Extraction - Scan otomatis semua file JavaScript yang terhubung

    ✅ Multi-threading - Scanning cepat dengan concurrent requests

    ✅ API Key Detection - Mendeteksi format API keys umum (Google, AWS, Stripe, GitHub, Slack, JWT)

    ✅ JSON Export - Simpan hasil scan untuk dokumentasi lebih lanjut

    ✅ User-Agent Customization - Hindari detection dengan custom headers

🎯 Use Cases

    Security Audit - Memeriksa apakah ada secrets yang terekspos di frontend

    Bug Bounty - Identifikasi misconfigurations pada target program bug bounty

    Compliance Testing - Pastikan tidak ada sensitive data yang bocor ke client-side

    Developer Education - Demonstrasi mengapa environment variables di frontend tidak aman

pip install requests beautifulsoup4

git clone https://github.com/riandecrypt/EnvHunter.git

cd EnvHunter

chmod +x env-hunter.py
