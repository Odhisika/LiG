import os
from xhtml2pdf import pisa

def convert_html_to_pdf(source_html, output_filename):
    # open output file for writing (truncated binary)
    result_file = open(output_filename, "w+b")

    # convert HTML to PDF
    pisa_status = pisa.CreatePDF(
            source_html,                # the HTML to convert
            dest=result_file)           # file handle to recieve result

    # close output file
    result_file.close()                 # close output file

    # return True on success and False on errors
    return pisa_status.err

if __name__ == "__main__":
    image_path = "/home/francis/.gemini/antigravity/brain/f92cab26-b619-40a4-8f44-f1aa6188dcd0/hubtel_flow_diagram_1778233958210.png"
    
    html_content = f"""
    <html>
    <head>
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}
            body {{
                font-family: 'Helvetica', 'Arial', sans-serif;
                color: #333;
                line-height: 1.6;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #0056b3;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }}
            h1 {{ color: #0056b3; }}
            h2 {{ color: #0056b3; border-left: 5px solid #0056b3; padding-left: 10px; margin-top: 30px; }}
            .flow-image {{
                width: 100%;
                margin: 20px 0;
            }}
            .footer {{
                position: fixed;
                bottom: 0;
                width: 100%;
                text-align: center;
                font-size: 10px;
                color: #777;
                border-top: 1px solid #eee;
                padding-top: 5px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 10px;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
                color: #0056b3;
            }}
            .note {{
                background-color: #e7f3ff;
                border-left: 6px solid #2196F3;
                padding: 10px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Hubtel API Integration Flow</h1>
            <p><strong>Project:</strong> LiG Store (E-commerce Platform)</p>
            <p><strong>Requirement:</strong> Hubtel UAT Requirement #5</p>
        </div>

        <h2>1. Visual Integration Flow</h2>
        <img src="{image_path}" class="flow-image">

        <h2>2. Technical Step-by-Step</h2>
        <p>The LiG Store integrates with Hubtel using a secure, server-side redirection model. Below are the technical stages of a single transaction:</p>
        
        <ul>
            <li><strong>Initiation:</strong> When a user checks out, the LiG backend calls Hubtel's <code>/items/initiate</code> endpoint with the order amount and a unique client reference.</li>
            <li><strong>Redirection:</strong> Hubtel returns a secure Checkout URL. The user is redirected from LiG to this page to choose their payment method (Momo or Card).</li>
            <li><strong>Asynchronous Callback (Webhook):</strong> Upon successful payment, Hubtel sends a <code>POST</code> request to LiG's webhook endpoint. This ensures the order is marked as paid even if the user closes their browser.</li>
            <li><strong>Final Verification:</strong> When the user is redirected back to LiG, the system performs a final real-time status check via the <code>/transactions/status</code> API for maximum security.</li>
        </ul>

        <div class="note">
            <strong>Security Note:</strong> All communication is encrypted via TLS 1.2+, and transactions are verified using server-to-server status checks to prevent client-side tampering.
        </div>

        <h2>3. API Endpoints</h2>
        <table>
            <tr>
                <th>Function</th>
                <th>Method</th>
                <th>Endpoint</th>
            </tr>
            <tr>
                <td>Initiate Checkout</td>
                <td>POST</td>
                <td>payproxyapi.hubtel.com/items/initiate</td>
            </tr>
            <tr>
                <td>Status Verification</td>
                <td>GET</td>
                <td>rmsc.hubtel.com/v1/merchantaccount/merchants/{{ID}}/transactions/status</td>
            </tr>
            <tr>
                <td>Webhook Endpoint</td>
                <td>POST</td>
                <td>lig-store.com/payment/hubtel-webhook/</td>
            </tr>
        </table>

        <div class="footer">
            &copy; 2026 LiG Store | Prepared for Hubtel UAT
        </div>
    </body>
    </html>
    """
    
    output_path = "/home/francis/Desktop/Projects/Lig/LiG/HUBTEL_INTEGRATION_FLOW.pdf"
    err = convert_html_to_pdf(html_content, output_path)
    
    if not err:
        print(f"Successfully generated PDF at: {{output_path}}")
    else:
        print(f"Error generating PDF: {{err}}")
