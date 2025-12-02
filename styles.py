"""
CSS and HTML styling constants for the Tesla Battery Analysis Dashboard.
"""

# Header CSS/HTML with Tesla Battery Analysis image and title
HEADER_HTML = """
<style>
    .header {
        display: flex;
        justify-content: center;
        align-items: center;
        flex-direction: column;
        padding: 0rem 0;
        margin-bottom: 0rem; /* Adjust the margin bottom to reduce space */
    }
    .header img {
        width: 100%;
        height: auto;
    }
    .header h1 {
        margin: 0;
        padding-top: 1rem;
        text-align: center;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 32px;
    }
    .header h1 span {
        margin: 0 10px;
    }
</style>
<div class="header">
    <img src="https://uploads.tff-forum.de/original/4X/5/2/3/52397973df71db6122c1eda4c5c558d2ca70686c.jpeg" alt="Tesla Battery Analysis">
    <h1><span>🔋</span> Tesla Battery Analysis <span>🔋</span></h1>
</div>
"""

# Google Forms logo with animated arrows and pulsing effect
GOOGLE_FORM_LOGO_HTML = """
<style>
    @keyframes pulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.05); opacity: 0.9; }
        100% { transform: scale(1); opacity: 1; }
    }
    .google-form-logo {
        display: block;
        margin: 0rem auto; /* Centers the logo horizontally below the header */
        width: 300px;  /* Adjust the width of the logo as necessary */
        height: auto;
        animation: pulse 2s infinite ease-in-out;
    }
    .arrow-text {
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 24px;
        font-weight: bold;
        margin-top: 20px;
    }
    .arrow {
        animation: blinker 3s linear infinite;
        font-size: 24px;
        margin: 0 20px; /* Increased spacing from text */
    }
    @keyframes blinker {
        50% {
            opacity: 0;
        }
    }
</style>
<div class="arrow-text">
    <span>Add your data here</span>
    <span class="arrow">🡢</span>
    <a href="https://forms.gle/WtFayqANSr9kwKv39" target="_blank">
        <img src="https://i.ibb.co/YZvSDRm/google-forms-400x182-removebg-preview.png" class="google-form-logo" alt="Google Forms Survey">
    </a>
    <span class="arrow">🡠</span>
    <span>Add your data here</span>
</div>
"""

# Latest Entries HTML label
LATEST_ENTRIES_HTML = """
<div>
    Latest Entries
</div>
"""

# Sidebar banner with logos and links
SIDEBAR_BANNER_HTML = """
<style>
    .sidebar-content {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0rem;
    }
    .sidebar-content img {
        height: auto;
    }
    .sidebar-content .akku-wiki {
        width: 90px;  /* Set specific width for Akku Wiki logo */
    }
    .sidebar-content .buy-me-coffee {
        width: 240px;  /* Set specific width for Buy Me a Coffee logo */
    }
    .sidebar-content .follow-on-x {
        width: 110px;  /* Set specific width for Follow on X logo */
    }
    .sidebar-content .text {
        text-align: center;
        font-size: 12px;  /* Default font size for text */
    }
    .sidebar-content a {
        color: white;
        text-decoration: none;
        font-weight: bold;
    }
</style>
<div class="sidebar-content">
    <a href="https://www.tesla.com/de_de/referral/julien95870" target="_blank">
        <div>
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Tesla_T_symbol.svg/482px-Tesla_T_symbol.svg.png" class="akku-wiki" alt="Akku Wiki">
            <div class="text">Referral</div>
        </div>
    </a>
    <a href="https://buymeacoffee.com/eivissa" target="_blank">
        <img src="https://media.giphy.com/media/o7RZbs4KAA6tvM4H6j/giphy.gif" class="buy-me-coffee" alt="Buy Me a Coffee">
    </a>
    <a href="https://x.com/eivissacopter" target="_blank">
        <img src="https://i.ibb.co/xLhFQNn/c23e7825a07e5e998bd361f9c991e12c-400x400-removebg-preview.png" class="follow-on-x" alt="Follow on X">
    </a>
</div>
"""
