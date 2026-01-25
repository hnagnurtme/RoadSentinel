// src/pages/AuthPage.tsx
import React, { useState } from 'react';
import { Share2, ShieldCheck, Home } from 'lucide-react';
import { authService } from '@/services/auth.service';
import type { RegisterRequest } from '@/types/index';

// --- Sub-components (để chung file cho gọn, bạn có thể tách ra) ---

const FeatureCard = ({ icon, label }: { icon: React.ReactNode; label: string }) => (
  <div className="flex flex-col items-center justify-center w-24 h-24 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm hover:bg-white/10 transition-colors cursor-default group">
    <div className="mb-2 p-2 rounded-lg bg-teal-500/10 group-hover:bg-teal-500/20 transition-colors">
      {icon}
    </div>
    <span className="text-[10px] font-bold tracking-wider text-slate-400 group-hover:text-slate-200 uppercase transition-colors">{label}</span>
  </div>
);

const InputField = (props: React.InputHTMLAttributes<HTMLInputElement> & { label: string }) => (
  <div className="space-y-1.5">
    <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-wider pl-1">
      {props.label}
    </label>
    <input 
      {...props}
      className="w-full bg-[#1e293b] border border-slate-700/50 text-white text-sm rounded-xl px-4 py-3.5 outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-all placeholder:text-slate-600 hover:border-slate-600"
    />
  </div>
);

// Icon Google SVG thuần
const GoogleIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M22.56 12.25C22.56 11.47 22.49 10.72 22.36 10H12V14.26H17.92C17.66 15.63 16.88 16.79 15.71 17.57V20.34H19.28C21.36 18.42 22.56 15.6 22.56 12.25Z" fill="#4285F4"/>
    <path d="M12 23C14.97 23 17.46 22.02 19.28 20.34L15.71 17.57C14.73 18.23 13.48 18.63 12 18.63C9.14 18.63 6.71 16.7 5.84 14.09H2.18V16.93C3.99 20.53 7.7 23 12 23Z" fill="#34A853"/>
    <path d="M5.84 14.09C5.62 13.43 5.49 12.73 5.49 12C5.49 11.27 5.62 10.57 5.84 9.91V7.07H2.18C1.43 8.55 1 10.22 1 12C1 13.78 1.43 15.45 2.18 16.93L5.84 14.09Z" fill="#FBBC05"/>
    <path d="M12 5.38C13.62 5.38 15.06 5.94 16.21 7.02L19.37 3.86C17.46 2.09 14.97 1 12 1C7.7 1 3.99 3.47 2.18 7.07L5.84 9.91C6.71 7.3 9.14 5.38 12 5.38Z" fill="#EA4335"/>
  </svg>
);

// --- Main Component ---

const AuthPage: React.FC = () => {
  const [isLogin, setIsLogin] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);
  
  // State form bao gồm tất cả các trường có thể có trong RegisterRequest
  const [formData, setFormData] = useState<RegisterRequest>({
    email: '',
    password: '',
    full_name: '',
    organization_name: ''
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isLogin) {
        // --- LOGIN FLOW ---
        // Chỉ lấy email và password theo đúng LoginRequest schema
        const res = await authService.login({
          email: formData.email,
          password: formData.password
        });
        
        console.log("Login Token Data:", res.data); // data là TokenResponse
        alert(`Login Successful!\nAccess Token: ${res.data?.access_token.slice(0, 15)}...`);
        // TODO: Lưu token vào localStorage và redirect
        
      } else {
        // --- REGISTER FLOW ---
        // Gửi toàn bộ formData theo RegisterRequest schema
        const res = await authService.register(formData);
        
        console.log("Registered User Data:", res.data); // data là UserResponse
        alert(`Register Successful!\nWelcome ${res.data?.full_name} (${res.data?.role})`);
        setIsLogin(true); // Chuyển về trang login sau khi đăng ký thành công
      }
    } catch (error: any) {
      alert("Error: " + (error.message || "Something went wrong"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#020408] text-white font-sans selection:bg-teal-500/30 selection:text-teal-200 overflow-hidden relative flex items-center justify-center p-4">
      
      {/* Background Glow Effects */}
      <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-teal-600/10 rounded-full blur-[150px] pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-5%] w-[40%] h-[40%] bg-cyan-600/5 rounded-full blur-[120px] pointer-events-none"></div>

      <div className="container max-w-6xl w-full flex flex-col md:flex-row items-center justify-between relative z-10 gap-10 md:gap-20">
        
        {/* === LEFT SECTION (Hero & Branding) === */}
        <div className="w-full md:w-1/2 flex flex-col items-start md:pr-10">
          {/* Logo */}
          <div className="flex items-center gap-3 mb-10">
            <div className="bg-gradient-to-tr from-teal-400 to-cyan-500 p-2.5 rounded-xl shadow-[0_0_20px_rgba(20,184,166,0.3)]">
              <Share2 size={24} className="text-white" strokeWidth={2.5} />
            </div>
            <span className="text-2xl font-bold tracking-tight text-white">PeerDrop</span>
          </div>

          {/* Hero Text */}
          <h1 className="text-5xl md:text-[4rem] font-bold leading-[1.1] mb-6 tracking-tight">
            Secure sharing <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-400 to-cyan-400">
              without boundaries.
            </span>
          </h1>

          <p className="text-slate-400 text-lg mb-12 max-w-lg leading-relaxed font-medium">
            Decentralized sharing reimagined for enterprise. Direct, encrypted, and built for modern scale.
          </p>

          {/* Feature Icons Grid */}
          <div className="flex gap-4 md:gap-6 self-start md:self-auto">
            <FeatureCard icon={<Share2 className="text-teal-400" />} label="Direct P2P" />
            <FeatureCard icon={<ShieldCheck className="text-teal-400" />} label="E2E Secure" />
            <FeatureCard icon={<Home className="text-teal-400" />} label="Private" />
          </div>
        </div>

        {/* === RIGHT SECTION (Auth Form Card) === */}
        <div className="w-full md:w-[480px] shrink-0">
          <div className="bg-[#0B1221] border border-white/5 p-8 md:p-10 rounded-[32px] shadow-2xl shadow-black/80 relative overflow-hidden">
            
            {/* Form Header */}
            <div className="mb-8 relative z-10">
              <h2 className="text-3xl font-bold text-white mb-2">
                {isLogin ? "Welcome Back" : "Create Account"}
              </h2>
              <p className="text-slate-400 text-sm">
                {isLogin ? "Enter your workspace credentials." : "Join PeerDrop today for free."}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5 relative z-10">
              
              {/* === REGISTER FIELDS === */}
              {!isLogin && (
                <>
                  <InputField 
                    label="Full Name"
                    name="full_name"
                    placeholder="John Doe"
                    value={formData.full_name}
                    onChange={handleChange}
                    required
                  />
                  <InputField 
                    label="Organization (Optional)"
                    name="organization_name"
                    placeholder="Acme Corp."
                    value={formData.organization_name || ''}
                    onChange={handleChange}
                  />
                </>
              )}

              {/* === COMMON FIELDS === */}
              <InputField 
                label="Email Address"
                type="email"
                name="email"
                placeholder="name@company.com"
                value={formData.email}
                onChange={handleChange}
                required
              />

              <InputField 
                label="Password"
                type="password"
                name="password"
                placeholder="••••••••••••"
                value={formData.password}
                onChange={handleChange}
                required
              />

              {/* Login Options */}
              {isLogin && (
                <div className="flex items-center justify-between text-sm pt-1">
                  <label className="flex items-center gap-2 cursor-pointer group select-none">
                    <div className="w-4 h-4 rounded border border-slate-600 bg-[#1e293b] group-hover:border-teal-500 transition-colors flex items-center justify-center">
                      {/* Fake checkbox check */}
                    </div>
                    <span className="text-slate-400 group-hover:text-slate-300 transition-colors">Remember me</span>
                  </label>
                  <a href="#" className="text-teal-400 hover:text-teal-300 font-medium transition-colors">
                    Forgot?
                  </a>
                </div>
              )}

              {/* Submit Button */}
              <button 
                type="submit" 
                disabled={loading}
                className="w-full py-3.5 px-4 bg-gradient-to-r from-teal-500 to-cyan-500 hover:from-teal-400 hover:to-cyan-400 text-white font-bold rounded-xl shadow-lg shadow-teal-500/20 transition-all transform hover:scale-[1.01] active:scale-[0.98] mt-2 disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                    Processing...
                  </span>
                ) : (
                  isLogin ? "Authenticate" : "Sign Up"
                )}
              </button>

              {/* Divider */}
              <div className="relative flex py-3 items-center">
                <div className="flex-grow border-t border-slate-800"></div>
                <span className="flex-shrink-0 mx-4 text-[10px] font-bold text-slate-600 tracking-widest uppercase">Secure SSO</span>
                <div className="flex-grow border-t border-slate-800"></div>
              </div>

              {/* Google Button */}
              <button type="button" className="w-full flex items-center justify-center gap-3 bg-[#1e293b] hover:bg-[#253146] border border-slate-700 hover:border-slate-600 text-white py-3.5 rounded-xl transition-all font-medium group">
                <GoogleIcon />
                <span className="group-hover:text-white text-slate-200">Continue with Google</span>
              </button>

              {/* Switch Auth Mode */}
              <p className="text-center text-slate-400 text-sm mt-4">
                {isLogin ? "New here? " : "Already have an account? "}
                <button 
                  type="button"
                  onClick={() => setIsLogin(!isLogin)} 
                  className="text-teal-400 hover:text-teal-300 font-medium underline underline-offset-4 hover:decoration-teal-300 transition-all"
                >
                  {isLogin ? "Create an account" : "Log in"}
                </button>
              </p>

            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthPage;