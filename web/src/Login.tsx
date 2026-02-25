// Inside your React Login component (Frontend)

const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
        // Update state
            const [formData, setFormData] = useState({
                email: '', // Changed from username
                password: ''
            })

            // Update API body in handleSubmit
            body: JSON.stringify({
                email: formData.email, // Changed from username
                password: formData.password
            })
        

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Login failed');
        }

        const data = await response.json();
        
        // Save the JWT token to local storage for future secure requests
        localStorage.setItem('vidyamitra_token', data.access_token);
        
        // Pass the user info back up to the parent component
        onLogin(data.user_info);

    } catch (err: any) {
        setError(err.message);
    } finally {
        setLoading(false);
    }
};