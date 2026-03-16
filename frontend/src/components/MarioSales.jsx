import React, { useState } from 'react';

const MarioSales = () => {
  // 1. Set up state to hold our 6 files and loading status
  const [files, setFiles] = useState({
    file_b2b_cgst: null,
    file_b2b_igst: null,
    file_b2c_cgst: null,
    file_b2c_igst: null,
    file_b2b_cn_cgst: null,
    file_b2b_cn_igst: null,
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');

  // 2. Handle when a user selects a file
  const handleFileChange = (e) => {
    const { name, files: selectedFiles } = e.target;
    setFiles((prevFiles) => ({
      ...prevFiles,
      [name]: selectedFiles[0] || null,
    }));
  };

  // 3. Handle the form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage('');

    // Package the files into FormData (this is how React sends files to Python)
    const formData = new FormData();
    let hasFiles = false;

    for (const key in files) {
      if (files[key]) {
        formData.append(key, files[key]);
        hasFiles = true;
      }
    }

    if (!hasFiles) {
      setMessage("Please upload at least one file!");
      setIsLoading(false);
      return;
    }

    try {
      // Send the request to our new Flask route
      // Note: adjust the URL if your Flask backend runs on a different port/link
      const response = await fetch('http://127.0.0.1:5000/api/mario/sales', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Something went wrong on the server.');
      }

      // Automatically download the returned Excel file
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = 'Mario_Combined_Sales.xlsx';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);

      setMessage('Success! File downloaded.');
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // 4. The Visual Interface (JSX)
  return (
    <div style={{ padding: '20px', maxWidth: '600px', margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <h2 style={{ color: '#333', borderBottom: '2px solid #007bff', paddingBottom: '10px' }}>
        Mario Sales Tax Converter
      </h2>
      <p style={{ color: '#666', marginBottom: '20px' }}>
        Upload your Odoo export files below. Leave empty if you have no data for a category.
      </p>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        
        {/* B2B Section */}
        <div style={{ background: '#f8f9fa', padding: '15px', borderRadius: '8px', border: '1px solid #dee2e6' }}>
          <h3 style={{ marginTop: 0, color: '#495057' }}>B2B Uploads</h3>
          <div style={{ marginBottom: '10px' }}>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '5px' }}>1. B2B CGST File</label>
            <input type="file" name="file_b2b_cgst" accept=".xlsx, .xls" onChange={handleFileChange} />
          </div>
          <div>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '5px' }}>2. B2B IGST File</label>
            <input type="file" name="file_b2b_igst" accept=".xlsx, .xls" onChange={handleFileChange} />
          </div>
        </div>

        {/* B2C Section */}
        <div style={{ background: '#f8f9fa', padding: '15px', borderRadius: '8px', border: '1px solid #dee2e6' }}>
          <h3 style={{ marginTop: 0, color: '#495057' }}>B2C Uploads</h3>
          <div style={{ marginBottom: '10px' }}>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '5px' }}>3. B2C CGST File</label>
            <input type="file" name="file_b2c_cgst" accept=".xlsx, .xls" onChange={handleFileChange} />
          </div>
          <div>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '5px' }}>4. B2C IGST File</label>
            <input type="file" name="file_b2c_igst" accept=".xlsx, .xls" onChange={handleFileChange} />
          </div>
        </div>

        {/* Credit Notes Section */}
        <div style={{ background: '#f8f9fa', padding: '15px', borderRadius: '8px', border: '1px solid #dee2e6' }}>
          <h3 style={{ marginTop: 0, color: '#495057' }}>Credit Notes (B2B)</h3>
          <div style={{ marginBottom: '10px' }}>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '5px' }}>5. B2B CGST Credit Note</label>
            <input type="file" name="file_b2b_cn_cgst" accept=".xlsx, .xls" onChange={handleFileChange} />
          </div>
          <div>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '5px' }}>6. B2B IGST Credit Note</label>
            <input type="file" name="file_b2b_cn_igst" accept=".xlsx, .xls" onChange={handleFileChange} />
          </div>
        </div>

        {/* Submit Button & Messages */}
        <button 
          type="submit" 
          disabled={isLoading}
          style={{ 
            padding: '12px 20px', 
            backgroundColor: isLoading ? '#6c757d' : '#28a745', 
            color: 'white', 
            border: 'none', 
            borderRadius: '4px', 
            cursor: isLoading ? 'not-allowed' : 'pointer',
            fontSize: '16px',
            fontWeight: 'bold',
            marginTop: '10px'
          }}
        >
          {isLoading ? 'Processing...' : 'Convert & Combine All'}
        </button>

        {message && (
          <div style={{ 
            padding: '10px', 
            marginTop: '10px', 
            borderRadius: '4px', 
            backgroundColor: message.includes('Error') ? '#f8d7da' : '#d4edda',
            color: message.includes('Error') ? '#721c24' : '#155724'
          }}>
            {message}
          </div>
        )}
      </form>
    </div>
  );
};

export default MarioSales;