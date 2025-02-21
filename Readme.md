<div style="display: flex; align-items: center; justify-content: center; padding: 20px; background-color: #1e1e2f; color: white; height: 150px;">
    <h2>🎉 Selected for Social Winter of Code 2025! 🎉</h2>
</div>



# SocioSell: Social Media to Product Listing Generator 🛍️

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688.svg)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248.svg)](https://www.mongodb.com/atlas)
[![Gemini AI](https://img.shields.io/badge/Gemini-1.5%20Pro-red.svg)](https://cloud.google.com/ai-platform)
[![TailwindCSS](https://img.shields.io/badge/Tailwind-CSS-38B2AC.svg)](https://tailwindcss.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Social Winter of Code](https://img.shields.io/badge/SWOC-2025-orange.svg)](https://swoc.tech)
[![Contributors](https://img.shields.io/github/contributors/Varsha-1605/SocioSell)](https://github.com/Varsha-1605/SocioSell/graphs/contributors)

<p align="center">
  An open-source initiative to transform social media content into comprehensive Amazon-style product listings using cutting-edge AI technology. </p>

[🌟 Features](#-features) •
[⚙️ Installation](#development-setup) •
[💡 API Endpoints](#-api-endpoints) •
[🤝 Contributing](#-contributing) •
[👥 Community](#-community)

<img src="https://raw.githubusercontent.com/Varsha-1605/SocioSell/main/static/banner.png" width="100%" alt="Project Banner"/>

</div>

---

## 🎯 Project Vision

SocioSell aims to bridge the gap between social media content and e-commerce by providing an open-source solution for automated product listing generation. Whether you're a developer, marketer, or e-commerce enthusiast, your contributions can help shape the future of social commerce.

## 📺 Project Demo

Watch our community demo:

[🎥 Watch Demo](https://github.com/Varsha-1605/SocioSell/blob/main/static/folder/Untitled%20video%20-%20Made%20with%20Clipchamp.mp4)

---
# Project WorkFlow Diagram:
![Image](https://github.com/user-attachments/assets/c23279b3-fc68-4603-b496-d6df93c1fb3d)

---

## 🌟 Features

<table>
  <tr>
    <td>
      <h3>🤖 AI-Powered Analysis</h3>
      <ul>
        <li>Google Generative AI integration</li>
        <li>Smart product detection</li>
        <li>Automatic feature extraction</li>
      </ul>
    </td>
    <td>
      <h3>🔄 Smart Processing</h3>
      <ul>
        <li>Real-time processing</li>
        <li>Async operations</li>
        <li>Intelligent matching</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td>
      <h3>🎯 Product Categories</h3>
      <ul>
        <li>Electronics</li>
        <li>Fashion</li>
        <li>Home Decor</li>
        <li>Beauty</li>
        <li>Sports Equipment</li>
      </ul>
    </td>
    <td>
      <h3>💫 User Experience</h3>
      <ul>
        <li>Modern UI/UX</li>
        <li>Drag-and-drop uploads</li>
        <li>Interactive comparisons</li>
      </ul>
    </td>
  </tr>
</table>

## ⚠️ Limitations  
- **Maximum Processing Capacity** (due to Gemini API constraints):  
  - **Images**: Up to 5 images per request.  
  - **Videos**: Up to 3 videos, each limited to 10 seconds in duration.  

## 🔧 Technology Stack

### Backend Infrastructure
```mermaid
graph LR
    A[Python 3.8+] --> B[FastAPI]
    B --> C[MongoDB]
    B --> D[Gemini AI]
    B --> E[AsyncIO]
```

### Frontend Technologies
```mermaid
graph LR
    A[HTML5] --> B[TailwindCSS]
    B --> C[JavaScript]
    C --> D[Font Awesome]
```

## Development Setup  

I. Clone the repository 
> ```  
>  git clone https://github.com/Varsha-1605/SocioSell.git  
> cd SocioSell
> ```  

II. Set up a virtual environment
> ```
> python -m venv venv  
> source venv/bin/activate  # Windows: > venv\Scripts\activate  
> ```
III. Install dependencies
> ```
> pip install -r requirements.txt  
> ```
IV. Create a `.env` file
> ```
> cat > .env << EOL  
> GOOGLE_API_KEY=your_google_api_key  
> MONGODB_URL=your_mongodb_connection_string  
> EOL  
> ```
V. Initialize the database
> ```
> python database_setup.py  
> ```
VII. Start the development server
> ```
> uvicorn main:app --reload  
> ```
VIII. Access the application
- Open your browser and go to `http://localhost:8000`.

### Troubleshooting Common Issues

1. Gemini API Connection
```bash
Error: Failed to connect to Gemini API
Solution: Ensure GOOGLE_API_KEY is properly set in .env file
```

2. MongoDB Connection
```bash
Error: MongoDB connection failed  
Solution: Verify MONGODB_URL format and network access.  
Format: MONGODB_URL=mongodb+srv://<username>:<password>@<cluster-address>/<database>?retryWrites=true&w=majority  
Replace <username>, <password>, <cluster-address>, and <database> with your details.
```

3. Image Processing
```bash
Error: Image processing failed
Solution: Verify image format (supported: jpg, png) and size (<5MB)
```

4. Metadata-generation-failed
```bash
Error: metadata-generation-failed
Solution: Install Microsoft C++ Build Tools and upgrade pip, setuptools, and wheel:
Python versions between 3.9 and 3.12 only
1. Install from https://visualstudio.microsoft.com/visual-cpp-build-tools/.
2. Run: pip install --upgrade pip setuptools wheel
```

## 📁 Documentation for Deployment

The detailed documentation for deployment is available in a separate file. Please refer to:
[📁 documentation](./Deploy_Documentation.md)

## 📁 Project Structure  

The detailed project structure is available in a separate file. Please refer to:  
[📁 Project Structure Details](./docs/PROJECT_STRUCTURE.md)

## 💡 API Endpoints

<table>
  <tr>
    <th>Endpoint</th>
    <th>Method</th>
    <th>Description</th>
  </tr>
  <tr>
    <td><code>/upload/</code></td>
    <td>POST</td>
    <td>Upload & analyze products</td>
  </tr>
  <tr>
    <td><code>/search/{title}</code></td>
    <td>GET</td>
    <td>Search product database</td>
  </tr>
  <tr>
    <td><code>/listings/{product_id}</code></td>
    <td>GET</td>
    <td>Get listing details</td>
  </tr>
  <tr>
    <td><code>/compare/{product_id}</code></td>
    <td>GET</td>
    <td>Compare products</td>
  </tr>
  <tr>
    <td><code>/health</code></td>
    <td>GET</td>
    <td>Check health status of DB</td>
  </tr>
  <tr>
    <td><code>/pool-stats</code></td>
    <td>GET</td>
    <td>Check pool status of DB</td>
  </tr>
</table>
The detailed API endpoints are available in a separate file. Please refer to:  
[💡 API Endpoints](./docs/PROJECT_STRUCTURE.md)

## 🤝 Contributing

We warmly welcome contributions from developers of all skill levels! Here's how you can help:

```mermaid
graph TD
    A[Fork Repository] --> B[Create Branch]
    B --> C[Make Changes]
    C --> D[Commit Changes]
    D --> E[Push to Branch]
    E --> F[Create Pull Request]
```

### **The detailed contributing guideline is available [here](./docs/CONTRIBUTING.md)**.

### Star this repository ⭐

## 👥 Community

- 💬 Join our [Discord Server](https://discord.gg/n34tSJ3TBs)
- 🔗 Connect on [LinkedIn](www.linkedin.com/in/varsha-dewangan-197983256)
- 🐦 Follow us on [Twitter]( https://x.com/varsha_dew454)
- 📧 Contact maintainers: varshadewangan1605@gmail.com

### 🌟 Contributors

Thanks to these wonderful people:

<a href="https://github.com/Varsha-1605/SocioSell/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Varsha-1605/SocioSell" />
</a>

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- All our amazing contributors
- [Social Winter of Code](https://socialwinterofcode.com/) for selecting our project
- [Google Generative AI](https://cloud.google.com/ai-platform)
- [MongoDB Atlas](https://www.mongodb.com/atlas)
- [TailwindCSS](https://tailwindcss.com/)
- [FastAPI](https://fastapi.tiangolo.com/)

---

<div align="center">

Made with ❤️ by the SocioSell Community

[⬆ Back to Top](#socialsell-social-media-to-product-listing-generator-)

</div>
