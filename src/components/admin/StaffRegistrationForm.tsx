// src/components/admin/StaffRegistrationForm.tsx
import React, { useState } from 'react';
import { backendApi } from '@/services/backendApi';

const roles = [
  'hod', 'assistant_professor', 'associate_professor',
  'professor', 'professor_sg', 'vp', 'dean'
];

const faculties = [
  'Faculty of Science and Humanities',
  'Faculty of Engineering and Technology',
  'Faculty of Management',
  'Faculty of Dental',
  'Faculty of SEAD'
];

const campuses = ['Ramapuram', 'KTR', 'Vadapalani', 'Trichirapalli'];

export default function StaffRegistrationForm() {
  const [form, setForm] = useState({
    name: '',
    employee_id: '',
    college: '',
    faculty: faculties[0],
    campus: campuses[0],
    contact_number: '',
    email: '',
    role: roles[0]
  });

  const [credentials, setCredentials] = useState<{ username: string; password: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setCredentials(null);

    const res = await backendApi.registerStaff(form);

    if (res.success && res.data?.credentials) {
      setCredentials(res.data.credentials);
    } else {
      alert(` Error: ${res.error}`);
    }

    setLoading(false);
  };

  return (
    <div className="max-w-xl mx-auto p-6 bg-white rounded-xl shadow-md">
      <h2 className="text-2xl font-semibold mb-4">Register New Staff</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <input name="name" placeholder="Full Name" onChange={handleChange} className="w-full border px-3 py-2 rounded" required />
        <input name="employee_id" placeholder="Employee ID" onChange={handleChange} className="w-full border px-3 py-2 rounded" required />
        <input name="college" placeholder="College" onChange={handleChange} className="w-full border px-3 py-2 rounded" required />

        <select name="faculty" onChange={handleChange} className="w-full border px-3 py-2 rounded">
          {faculties.map(f => <option key={f}>{f}</option>)}
        </select>

        <select name="campus" onChange={handleChange} className="w-full border px-3 py-2 rounded">
          {campuses.map(c => <option key={c}>{c}</option>)}
        </select>

        <input name="contact_number" placeholder="Phone Number" onChange={handleChange} className="w-full border px-3 py-2 rounded" required />
        <input name="email" placeholder="Email" type="email" onChange={handleChange} className="w-full border px-3 py-2 rounded" required />

        <select name="role" onChange={handleChange} className="w-full border px-3 py-2 rounded">
          {roles.map(r => <option key={r} value={r}>{r.replace(/_/g, ' ').toUpperCase()}</option>)}
        </select>

        <button type="submit" disabled={loading} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          {loading ? 'Registering...' : 'Register Staff'}
        </button>
      </form>

      {credentials && (
        <div className="mt-6 p-4 bg-green-100 border border-green-300 rounded">
          <p className="font-medium"> Staff Registered!</p>
          <p><strong>Username:</strong> {credentials.username}</p>
          <p><strong>Password:</strong> {credentials.password}</p>
        </div>
      )}
    </div>
  );
}
