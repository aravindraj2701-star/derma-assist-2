import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../api/api';
import './ProfilePage.css';

export default function ProfilePage() {
  const { user, logout, updateProfile, refreshUser } = useAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState('contact');
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // Form State
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    address: '',
    city: '',
    state: '',
    zip_code: '',
    country: '',
    date_of_birth: '',
    gender: '',
    blood_group: '',
    skin_type: '',
    allergies: '',
    medical_history: '',
    current_medications: '',
    bio: '',
    specialization: '',
    hospital_affiliation: '',
    license_number: '',
    emergency_contact: '',
    emergency_phone: '',
  });

  // Password Change Form State
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [passwordError, setPasswordError] = useState('');

  // Forgot Password / Reset Link State
  const [isRequestingReset, setIsRequestingReset] = useState(false);
  const [resetMessage, setResetMessage] = useState('');
  const [generatedResetLink, setGeneratedResetLink] = useState('');
  const [copiedLink, setCopiedLink] = useState(false);

  // Sync formData from user
  useEffect(() => {
    if (user) {
      setFormData({
        name: user.name || '',
        phone: user.phone || '',
        address: user.address || '',
        city: user.city || '',
        state: user.state || '',
        zip_code: user.zip_code || '',
        country: user.country || '',
        date_of_birth: user.date_of_birth || '',
        gender: user.gender || '',
        blood_group: user.blood_group || '',
        skin_type: user.skin_type || '',
        allergies: user.allergies || '',
        medical_history: user.medical_history || '',
        current_medications: user.current_medications || '',
        bio: user.bio || '',
        specialization: user.specialization || '',
        hospital_affiliation: user.hospital_affiliation || '',
        license_number: user.license_number || '',
        emergency_contact: user.emergency_contact || '',
        emergency_phone: user.emergency_phone || '',
      });
    }
  }, [user]);

  // Handle Input Changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  // Save Profile Changes
  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');
    setIsSaving(true);

    const result = await updateProfile(formData);
    setIsSaving(false);

    if (result.success) {
      setSuccessMessage('Profile details successfully updated and synchronized.');
      setIsEditing(false);
      setTimeout(() => setSuccessMessage(''), 5000);
    } else {
      setErrorMessage(result.error || 'Failed to update profile.');
    }
  };

  // Cancel Editing
  const handleCancelEdit = () => {
    if (user) {
      setFormData({
        name: user.name || '',
        phone: user.phone || '',
        address: user.address || '',
        city: user.city || '',
        state: user.state || '',
        zip_code: user.zip_code || '',
        country: user.country || '',
        date_of_birth: user.date_of_birth || '',
        gender: user.gender || '',
        blood_group: user.blood_group || '',
        skin_type: user.skin_type || '',
        allergies: user.allergies || '',
        medical_history: user.medical_history || '',
        current_medications: user.current_medications || '',
        bio: user.bio || '',
        specialization: user.specialization || '',
        hospital_affiliation: user.hospital_affiliation || '',
        license_number: user.license_number || '',
        emergency_contact: user.emergency_contact || '',
        emergency_phone: user.emergency_phone || '',
      });
    }
    setIsEditing(false);
    setErrorMessage('');
  };

  // Trigger Change Password
  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess('');

    if (!currentPassword) {
      setPasswordError('Please enter your current password.');
      return;
    }
    if (newPassword.length < 6) {
      setPasswordError('New password must be at least 6 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match.');
      return;
    }

    setIsChangingPassword(true);
    try {
      const res = await authAPI.changePassword(currentPassword, newPassword);
      setPasswordSuccess(res.data?.message || 'Password changed successfully.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setPasswordSuccess(''), 5000);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to change password. Please check your credentials.';
      setPasswordError(msg);
    } finally {
      setIsChangingPassword(false);
    }
  };

  // Trigger Password Reset Link Email / Token
  const handleRequestPasswordReset = async () => {
    if (!user?.email) return;
    setIsRequestingReset(true);
    setResetMessage('');
    setGeneratedResetLink('');
    setCopiedLink(false);

    try {
      const res = await authAPI.forgotPassword(user.email);
      setResetMessage(res.data?.message || 'Password reset link has been dispatched to your email.');
      if (res.data?.reset_link) {
        setGeneratedResetLink(res.data.reset_link);
      }
    } catch (err) {
      setResetMessage('Failed to request password reset link. Please try again.');
    } finally {
      setIsRequestingReset(false);
    }
  };

  // Copy Reset Link to Clipboard
  const handleCopyResetLink = () => {
    if (!generatedResetLink) return;
    navigator.clipboard.writeText(generatedResetLink);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 3000);
  };

  // Handle Logout
  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="profile-page-container">
      {/* Hero Profile Card */}
      <div className="profile-hero-card animate-fade-in">
        <div className="profile-hero-left">
          <div className="profile-avatar-large">
            {user?.picture ? (
              <img src={user.picture} alt={user?.name || 'User'} />
            ) : (
              user?.name?.charAt(0)?.toUpperCase() || '👤'
            )}
          </div>
          <div className="profile-hero-info">
            <div className="profile-hero-name">
              {user?.name || 'Practitioner'}
              <span className={`role-badge ${user?.role || 'patient'}`}>
                {user?.role === 'doctor' ? '🩺 Clinician' : user?.role === 'admin' ? '🛡️ Admin' : '👤 Patient'}
              </span>
            </div>
            <p className="profile-hero-email">
              <span>✉️</span> {user?.email || '—'}
            </p>
            <div className="profile-hero-meta">
              <span className="profile-hero-meta-item">
                <strong>ID:</strong> #{user?.user_id || '—'}
              </span>
              <span className="profile-hero-meta-item">
                <strong>Auth:</strong> {user?.picture ? 'Google OAuth' : 'Email & Password'}
              </span>
              {user?.created_at && (
                <span className="profile-hero-meta-item">
                  <strong>Member Since:</strong> {new Date(user.created_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="profile-hero-actions">
          {!isEditing ? (
            <button
              type="button"
              className="btn btn-primary btn-md"
              onClick={() => setIsEditing(true)}
            >
              ✏️ Edit Profile
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-secondary btn-md"
              onClick={handleCancelEdit}
              disabled={isSaving}
            >
              ✖ Cancel
            </button>
          )}
          <button
            type="button"
            className="btn btn-outline btn-md"
            onClick={handleLogout}
            style={{ color: 'var(--danger)', borderColor: 'var(--danger-border)' }}
          >
            🚪 Sign Out
          </button>
        </div>
      </div>

      {/* Notification Banners */}
      {successMessage && (
        <div className="profile-alert profile-alert-success">
          <span>✅</span>
          <span>{successMessage}</span>
        </div>
      )}
      {errorMessage && (
        <div className="profile-alert profile-alert-error">
          <span>⚠️</span>
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Tabs Navigation */}
      <div className="profile-nav-tabs" role="tablist">
        <button
          type="button"
          className={`profile-tab-btn ${activeTab === 'contact' ? 'active' : ''}`}
          onClick={() => setActiveTab('contact')}
        >
          📍 Contact &amp; Location
        </button>
        <button
          type="button"
          className={`profile-tab-btn ${activeTab === 'clinical' ? 'active' : ''}`}
          onClick={() => setActiveTab('clinical')}
        >
          🩺 Clinical &amp; Skin Profile
        </button>
        {(user?.role === 'doctor' || user?.role === 'admin' || isEditing || formData.specialization) && (
          <button
            type="button"
            className={`profile-tab-btn ${activeTab === 'doctor' ? 'active' : ''}`}
            onClick={() => setActiveTab('doctor')}
          >
            👨‍⚕️ Clinician Credentials
          </button>
        )}
        <button
          type="button"
          className={`profile-tab-btn ${activeTab === 'emergency' ? 'active' : ''}`}
          onClick={() => setActiveTab('emergency')}
        >
          🚨 Emergency Contact
        </button>
        <button
          type="button"
          className={`profile-tab-btn ${activeTab === 'security' ? 'active' : ''}`}
          onClick={() => setActiveTab('security')}
        >
          🔐 Security &amp; Password Reset
        </button>
      </div>

      {/* Tab 1: Contact & Location */}
      {activeTab === 'contact' && (
        <div className="profile-section-card animate-fade-in">
          <div className="profile-section-header">
            <div>
              <h3 className="profile-section-title">📍 Contact &amp; Geographic Location</h3>
              <p className="profile-section-subtitle">
                Phone number, clinic/residential address, and location details for reports and communication.
              </p>
            </div>
            {isEditing && <span className="badge badge-primary">Editing Mode</span>}
          </div>

          {!isEditing ? (
            <div className="profile-grid-2">
              <div className="info-field-group">
                <span className="info-label">Full Name</span>
                <span className="info-value">{user?.name || '—'}</span>
              </div>
              <div className="info-field-group">
                <span className="info-label">Phone Number</span>
                <span className={`info-value ${!user?.phone ? 'empty' : ''}`}>
                  {user?.phone || 'Not provided'}
                </span>
              </div>
              <div className="info-field-group" style={{ gridColumn: '1 / -1' }}>
                <span className="info-label">Street Address</span>
                <span className={`info-value ${!user?.address ? 'empty' : ''}`}>
                  {user?.address || 'Not provided'}
                </span>
              </div>
              <div className="info-field-group">
                <span className="info-label">City</span>
                <span className={`info-value ${!user?.city ? 'empty' : ''}`}>
                  {user?.city || 'Not provided'}
                </span>
              </div>
              <div className="info-field-group">
                <span className="info-label">State / Province</span>
                <span className={`info-value ${!user?.state ? 'empty' : ''}`}>
                  {user?.state || 'Not provided'}
                </span>
              </div>
              <div className="info-field-group">
                <span className="info-label">Postal / ZIP Code</span>
                <span className={`info-value ${!user?.zip_code ? 'empty' : ''}`}>
                  {user?.zip_code || 'Not provided'}
                </span>
              </div>
              <div className="info-field-group">
                <span className="info-label">Country</span>
                <span className={`info-value ${!user?.country ? 'empty' : ''}`}>
                  {user?.country || 'Not provided'}
                </span>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSaveProfile}>
              <div className="profile-grid-2">
                <div className="profile-form-group">
                  <label className="profile-label" htmlFor="name">Full Name *</label>
                  <input
                    id="name"
                    name="name"
                    type="text"
                    className="profile-input"
                    value={formData.name}
                    onChange={handleInputChange}
                    required
                  />
                </div>
                <div className="profile-form-group">
                  <label className="profile-label" htmlFor="phone">Phone Number</label>
                  <input
                    id="phone"
                    name="phone"
                    type="tel"
                    className="profile-input"
                    placeholder="+1 (555) 000-0000"
                    value={formData.phone}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="profile-form-group full-width">
                  <label className="profile-label" htmlFor="address">Street Address</label>
                  <input
                    id="address"
                    name="address"
                    type="text"
                    className="profile-input"
                    placeholder="123 Medical Parkway, Suite 400"
                    value={formData.address}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="profile-form-group">
                  <label className="profile-label" htmlFor="city">City</label>
                  <input
                    id="city"
                    name="city"
                    type="text"
                    className="profile-input"
                    placeholder="e.g. San Francisco"
                    value={formData.city}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="profile-form-group">
                  <label className="profile-label" htmlFor="state">State / Province</label>
                  <input
                    id="state"
                    name="state"
                    type="text"
                    className="profile-input"
                    placeholder="e.g. California"
                    value={formData.state}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="profile-form-group">
                  <label className="profile-label" htmlFor="zip_code">Postal / ZIP Code</label>
                  <input
                    id="zip_code"
                    name="zip_code"
                    type="text"
                    className="profile-input"
                    placeholder="94103"
                    value={formData.zip_code}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="profile-form-group">
                  <label className="profile-label" htmlFor="country">Country</label>
                  <input
                    id="country"
                    name="country"
                    type="text"
                    className="profile-input"
                    placeholder="e.g. United States"
                    value={formData.country}
                    onChange={handleInputChange}
                  />
                </div>
              </div>

              <div className="profile-footer-actions">
                <button
                  type="button"
                  className="btn btn-secondary btn-md"
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary btn-md"
                  disabled={isSaving}
                >
                  {isSaving ? 'Saving Changes...' : '💾 Save Contact Info'}
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {/* Tab 2: Clinical & Skin Profile */}
      {activeTab === 'clinical' && (
        <div className="profile-section-card animate-fade-in">
          <div className="profile-section-header">
            <div>
              <h3 className="profile-section-title">🩺 Clinical &amp; Dermatology Health Profile</h3>
              <p className="profile-section-subtitle">
                Patient baseline biometric data, Fitzpatrick phototype, allergies, and medical history.
              </p>
            </div>
            {isEditing && <span className="badge badge-primary">Editing Mode</span>}
          </div>

          {!isEditing ? (
            <div className="profile-grid-2">
              <div className="info-field-group">
                <span className="info-label">Date of Birth</span>
                <span className={`info-value ${!user?.date_of_birth ? 'empty' : ''}`}>
                  {user?.date_of_birth || 'Not specified'}
                </span>
              </div>
              <div className="info-field-group">
                <span className="info-label">Gender</span>
                <span className={`info-value ${!user?.gender ? 'empty' : ''}`}>
                  {user?.gender || 'Not specified'}
                </span>
              </div>
              <div className="info-field-group">
                <span className="info-label">Blood Group</span>
                <span className={`info-value ${!user?.blood_group ? 'empty' : ''}`}>
                  {user?.blood_group || 'Not specified'}
                </span>
              </div>
              <div className="info-field-group">
                <span className="info-label">Fitzpatrick Skin Phototype</span>
                <span className={`info-value ${!user?.skin_type ? 'empty' : ''}`}>
                  {user?.skin_type || 'Not specified'}
                </span>
              </div>
              <div className="info-field-group" style={{ gridColumn: '1 / -1' }}>
                <span className="info-label">Known Allergies (Skin &amp; Drug)</span>
                <span className={`info-value ${!user?.allergies ? 'empty' : ''}`}>
                  {user?.allergies || 'None reported'}
                </span>
              </div>
              <div className="info-field-group" style={{ gridColumn: '1 / -1' }}>
                <span className="info-label">Past Medical History / Dermatological Conditions</span>
                <span className={`info-value ${!user?.medical_history ? 'empty' : ''}`}>
                  {user?.medical_history || 'None reported'}
                </span>
              </div>
              <div className="info-field-group" style={{ gridColumn: '1 / -1' }}>
                <span className="info-label">Current Medications &amp; Topicals</span>
                <span className={`info-value ${!user?.current_medications ? 'empty' : ''}`}>
                  {user?.current_medications || 'None reported'}
                </span>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSaveProfile}>
              <div className="profile-grid-2">
                <div className="profile-form-group">
                  <label className="profile-label" htmlFor="date_of_birth">Date of Birth</label>
                  <input
                    id="date_of_birth"
                    name="date_of_birth"
                    type="date"
                    className="profile-input"
                    value={formData.date_of_birth}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="profile-form-group">
                  <label className="profile-label" htmlFor="gender">Gender</label>
                  <select
                    id="gender"
                    name="gender"
                    className="profile-select"
                    value={formData.gender}
                    onChange={handleInputChange}
                  >
                    <option value="">Select Gender</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Non-Binary">Non-Binary</option>
                    <option value="Prefer not to say">Prefer not to say</option>
                  </select>
                </div>
                <div className="profile-form-group">
                  <label className="profile-label" htmlFor="blood_group">Blood Group</label>
                  <select
                    id="blood_group"
                    name="blood_group"
                    className="profile-select"
                    value={formData.blood_group}
                    onChange={handleInputChange}
                  >
                    <option value="">Select Blood Group</option>
                    <option value="A+">A+</option>
                    <option value="A-">A-</option>
                    <option value="B+">B+</option>
                    <option value="B-">B-</option>
                    <option value="AB+">AB+</option>
                    <option value="AB-">AB-</option>
                    <option value="O+">O+</option>
                    <option value="O-">O-</option>
                  </select>
                </div>
                <div className="profile-form-group">
                  <label className="profile-label" htmlFor="skin_type">Fitzpatrick Skin Phototype</label>
                  <select
                    id="skin_type"
                    name="skin_type"
                    className="profile-select"
                    value={formData.skin_type}
                    onChange={handleInputChange}
                  >
                    <option value="">Select Skin Type</option>
                    <option value="Type I (Pale white, always burns, never tans)">Type I (Pale white, always burns)</option>
                    <option value="Type II (Fair, usually burns, tans minimally)">Type II (Fair, usually burns)</option>
                    <option value="Type III (Medium, sometimes mild burn, tans uniformly)">Type III (Medium / Olive)</option>
                    <option value="Type IV (Olive / Light Brown, rarely burns)">Type IV (Olive / Light Brown)</option>
                    <option value="Type V (Brown, very rarely burns, tans easily)">Type V (Brown / Dark Olive)</option>
                    <option value="Type VI (Dark Brown to Black, never burns)">Type VI (Deep Dark / Black)</option>
                  </select>
                </div>
                <div className="profile-form-group full-width">
                  <label className="profile-label" htmlFor="allergies">Known Allergies (Latex, Antibiotics, Fragrances, Sunscreens)</label>
                  <textarea
                    id="allergies"
                    name="allergies"
                    className="profile-textarea"
                    placeholder="e.g. Penicillin, Nickel contact allergy, Fragrance sensitizer"
                    value={formData.allergies}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="profile-form-group full-width">
                  <label className="profile-label" htmlFor="medical_history">Medical History (Eczema, Psoriasis, Melanoma history, etc.)</label>
                  <textarea
                    id="medical_history"
                    name="medical_history"
                    className="profile-textarea"
                    placeholder="e.g. Mild Atopic Dermatitis since childhood, No family history of melanoma"
                    value={formData.medical_history}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="profile-form-group full-width">
                  <label className="profile-label" htmlFor="current_medications">Current Medications &amp; Topicals</label>
                  <textarea
                    id="current_medications"
                    name="current_medications"
                    className="profile-textarea"
                    placeholder="e.g. Hydrocortisone 1% topical, Daily Cetirizine"
                    value={formData.current_medications}
                    onChange={handleInputChange}
                  />
                </div>
              </div>

              <div className="profile-footer-actions">
                <button
                  type="button"
                  className="btn btn-secondary btn-md"
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary btn-md"
                  disabled={isSaving}
                >
                  {isSaving ? 'Saving Changes...' : '💾 Save Clinical Profile'}
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {/* Tab 3: Clinician Credentials */}
      {activeTab === 'doctor' && (
        <div className="profile-section-card animate-fade-in">
          <div className="profile-section-header">
            <div>
              <h3 className="profile-section-title">👨‍⚕️ Clinical Practitioner &amp; Doctor Credentials</h3>
              <p className="profile-section-subtitle">
                Medical licenses, practice affiliations, and clinical specialization info.
              </p>
            </div>
            {isEditing && <span className="badge badge-primary">Editing Mode</span>}
          </div>

          {!isEditing ? (
            <div className="profile-grid-2">
              <div className="info-field-group">
                <span className="info-label">Clinical Specialization</span>
                <span className={`info-value ${!user?.specialization ? 'empty' : ''}`}>
                  {user?.specialization || 'Dermatology / General Practice'}
                </span>
              </div>
              <div className="info-field-group">
                <span className="info-label">Medical License Number</span>
                <span className={`info-value ${!user?.license_number ? 'empty' : ''}`}>
                  {user?.license_number || 'Not provided'}
                </span>
              </div>
              <div className="info-field-group" style={{ gridColumn: '1 / -1' }}>
                <span className="info-label">Hospital / Clinic Affiliation</span>
                <span className={`info-value ${!user?.hospital_affiliation ? 'empty' : ''}`}>
                  {user?.hospital_affiliation || 'Not provided'}
                </span>
              </div>
              <div className="info-field-group" style={{ gridColumn: '1 / -1' }}>
                <span className="info-label">Professional Bio / Summary</span>
                <span className={`info-value ${!user?.bio ? 'empty' : ''}`}>
                  {user?.bio || 'No practitioner bio added.'}
                </span>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSaveProfile}>
              <div className="profile-grid-2">
                <div className="profile-form-group">
                  <label className="profile-label" htmlFor="specialization">Clinical Specialization</label>
                  <input
                    id="specialization"
                    name="specialization"
                    type="text"
                    className="profile-input"
                    placeholder="e.g. Clinical Dermatology, Pediatric Dermatology"
                    value={formData.specialization}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="profile-form-group">
                  <label className="profile-label" htmlFor="license_number">Medical License Number</label>
                  <input
                    id="license_number"
                    name="license_number"
                    type="text"
                    className="profile-input"
                    placeholder="e.g. MD-982410-CA"
                    value={formData.license_number}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="profile-form-group full-width">
                  <label className="profile-label" htmlFor="hospital_affiliation">Hospital / Clinic Affiliation</label>
                  <input
                    id="hospital_affiliation"
                    name="hospital_affiliation"
                    type="text"
                    className="profile-input"
                    placeholder="e.g. Bayview Dermatology Medical Center"
                    value={formData.hospital_affiliation}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="profile-form-group full-width">
                  <label className="profile-label" htmlFor="bio">Professional Bio &amp; Qualifications</label>
                  <textarea
                    id="bio"
                    name="bio"
                    className="profile-textarea"
                    placeholder="Board-certified dermatologist with focus in dermoscopy, cutaneous oncology..."
                    value={formData.bio}
                    onChange={handleInputChange}
                  />
                </div>
              </div>

              <div className="profile-footer-actions">
                <button
                  type="button"
                  className="btn btn-secondary btn-md"
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary btn-md"
                  disabled={isSaving}
                >
                  {isSaving ? 'Saving Changes...' : '💾 Save Practitioner Credentials'}
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {/* Tab 4: Emergency Contacts */}
      {activeTab === 'emergency' && (
        <div className="profile-section-card animate-fade-in">
          <div className="profile-section-header">
            <div>
              <h3 className="profile-section-title">🚨 Emergency Contact Information</h3>
              <p className="profile-section-subtitle">
                Designated primary emergency contact person in the event of severe dermatological emergencies or clinical alerts.
              </p>
            </div>
            {isEditing && <span className="badge badge-primary">Editing Mode</span>}
          </div>

          {!isEditing ? (
            <div className="profile-grid-2">
              <div className="info-field-group">
                <span className="info-label">Emergency Contact Name</span>
                <span className={`info-value ${!user?.emergency_contact ? 'empty' : ''}`}>
                  {user?.emergency_contact || 'Not provided'}
                </span>
              </div>
              <div className="info-field-group">
                <span className="info-label">Emergency Phone Number</span>
                <span className={`info-value ${!user?.emergency_phone ? 'empty' : ''}`}>
                  {user?.emergency_phone || 'Not provided'}
                </span>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSaveProfile}>
              <div className="profile-grid-2">
                <div className="profile-form-group">
                  <label className="profile-label" htmlFor="emergency_contact">Emergency Contact Name</label>
                  <input
                    id="emergency_contact"
                    name="emergency_contact"
                    type="text"
                    className="profile-input"
                    placeholder="e.g. Jane Doe (Spouse / Guardian)"
                    value={formData.emergency_contact}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="profile-form-group">
                  <label className="profile-label" htmlFor="emergency_phone">Emergency Phone Number</label>
                  <input
                    id="emergency_phone"
                    name="emergency_phone"
                    type="tel"
                    className="profile-input"
                    placeholder="+1 (555) 999-8888"
                    value={formData.emergency_phone}
                    onChange={handleInputChange}
                  />
                </div>
              </div>

              <div className="profile-footer-actions">
                <button
                  type="button"
                  className="btn btn-secondary btn-md"
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary btn-md"
                  disabled={isSaving}
                >
                  {isSaving ? 'Saving Changes...' : '💾 Save Emergency Contact'}
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {/* Tab 5: Security & Password Reset */}
      {activeTab === 'security' && (
        <div className="profile-section-card animate-fade-in">
          <div className="profile-section-header">
            <div>
              <h3 className="profile-section-title">🔐 Account Security &amp; Password Management</h3>
              <p className="profile-section-subtitle">
                Generate secure password reset links, update your clinical account password, and manage session safety.
              </p>
            </div>
          </div>

          {/* 1-Click Password Reset Link Generator */}
          <div className="password-reset-box">
            <div className="password-reset-box-header">
              <span className="reset-icon-badge">🔑</span>
              <div className="reset-box-content">
                <h4 className="reset-box-title">Generate Password Reset Link</h4>
                <p className="reset-box-desc">
                  Need to reset your password or test the recovery link? Click below to generate an authorized token and dispatch an email to <strong>{user?.email}</strong>.
                </p>

                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={handleRequestPasswordReset}
                    disabled={isRequestingReset}
                  >
                    {isRequestingReset ? 'Generating Link...' : '⚡ Send / Generate Reset Link'}
                  </button>
                  <Link
                    to="/forgot-password"
                    className="btn btn-outline btn-sm"
                    style={{ textDecoration: 'none' }}
                  >
                    Open Recovery Portal &rarr;
                  </Link>
                </div>

                {resetMessage && (
                  <p style={{ marginTop: '0.75rem', fontSize: '0.88rem', color: 'var(--teal-900)', fontWeight: 600 }}>
                    {resetMessage}
                  </p>
                )}

                {generatedResetLink && (
                  <div className="reset-link-display-box animate-fade-in">
                    <span className="reset-link-text">{generatedResetLink}</span>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={handleCopyResetLink}
                    >
                      {copiedLink ? '✓ Copied!' : '📋 Copy Link'}
                    </button>
                    <a
                      href={generatedResetLink}
                      className="btn btn-primary btn-sm"
                      style={{ textDecoration: 'none' }}
                    >
                      Open Link ↗
                    </a>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* In-App Direct Password Change Form (for non-Google accounts) */}
          <div style={{ marginTop: '2rem' }}>
            <h4 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
              🔒 Change Account Password
            </h4>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
              Update your account password directly by providing your current password.
            </p>

            {passwordSuccess && (
              <div className="profile-alert profile-alert-success">
                <span>✅</span>
                <span>{passwordSuccess}</span>
              </div>
            )}
            {passwordError && (
              <div className="profile-alert profile-alert-error">
                <span>⚠️</span>
                <span>{passwordError}</span>
              </div>
            )}

            <form onSubmit={handleChangePassword} style={{ maxWidth: 500 }}>
              <div className="profile-form-group" style={{ marginBottom: '1rem' }}>
                <label className="profile-label" htmlFor="current_pwd">Current Password</label>
                <input
                  id="current_pwd"
                  type="password"
                  className="profile-input"
                  placeholder="Enter current password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                />
              </div>
              <div className="profile-form-group" style={{ marginBottom: '1rem' }}>
                <label className="profile-label" htmlFor="new_pwd">New Password</label>
                <input
                  id="new_pwd"
                  type="password"
                  className="profile-input"
                  placeholder="At least 6 characters"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                />
              </div>
              <div className="profile-form-group" style={{ marginBottom: '1.5rem' }}>
                <label className="profile-label" htmlFor="confirm_pwd">Confirm New Password</label>
                <input
                  id="confirm_pwd"
                  type="password"
                  className="profile-input"
                  placeholder="Re-enter new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-md"
                disabled={isChangingPassword}
              >
                {isChangingPassword ? 'Updating Password...' : '🛡️ Update Password'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
