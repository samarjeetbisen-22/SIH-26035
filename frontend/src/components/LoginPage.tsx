import React, { useState } from "react";
import {
  Award,
  Shield,
  Building,
  UserCheck,
  Lock,
  User,
  ArrowRight,
  AlertCircle,
  Eye,
  EyeOff,
  Scale,
  CheckCircle2,
} from "lucide-react";
import { UserSession, loginUser } from "../utils/apiClient";

interface LoginPageProps {
  onLoginSuccess: (user: UserSession) => void;
}

interface RolePreset {
  role: "INSPECTOR" | "REVIEWER" | "OWNER" | "ADMIN";
  label: "Technician" | "Reviewer" | "Instrument Owner" | "Admin";
  name: string;
  org: string;
  username: string;
  pwd: string;
  icon: React.ComponentType<{ className?: string }>;
  badgeColor: string;
}

const PRESET_ROLES: RolePreset[] = [
  {
    role: "INSPECTOR",
    label: "Technician",
    name: "Rajesh Kumar (Technician)",
    org: "RRSL Metrology Dept",
    username: "rajesh_inspector",
    pwd: "Inspector@123",
    icon: Award,
    badgeColor: "border-blue-200 bg-blue-50/60 text-blue-700",
  },
  {
    role: "REVIEWER",
    label: "Reviewer",
    name: "Dr. Priya Verma",
    org: "NABL Certified Reviewer",
    username: "priya_reviewer",
    pwd: "Reviewer@123",
    icon: Shield,
    badgeColor: "border-purple-200 bg-purple-50/60 text-purple-700",
  },
  {
    role: "ADMIN",
    label: "Admin",
    name: "Dr. V. K. Ramanathan",
    org: "Legal Metrology HQ",
    username: "admin",
    pwd: "Admin@123",
    icon: UserCheck,
    badgeColor: "border-amber-200 bg-amber-50/60 text-amber-700",
  },
  {
    role: "OWNER",
    label: "Instrument Owner",
    name: "Essae Digitronics",
    org: "Essae Fleet Portal",
    username: "essae_owner",
    pwd: "Owner@123",
    icon: Building,
    badgeColor: "border-emerald-200 bg-emerald-50/60 text-emerald-700",
  },
];

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  // Autofill initial credentials with Technician (Rajesh Kumar)
  const [selectedRole, setSelectedRole] = useState<RolePreset>(PRESET_ROLES[0]);
  const [username, setUsername] = useState<string>(PRESET_ROLES[0].username);
  const [password, setPassword] = useState<string>(PRESET_ROLES[0].pwd);
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSelectPreset = (preset: RolePreset) => {
    setSelectedRole(preset);
    setUsername(preset.username);
    setPassword(preset.pwd);
    setErrorMessage(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setErrorMessage("Please enter both username and password.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await loginUser(username.trim(), password);
      if (res.success && res.user) {
        onLoginSuccess(res.user);
      } else {
        setErrorMessage(
          res.error || "Authentication failed. Invalid username or password.",
        );
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to reach backend server.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col justify-center py-12 sm:px-6 lg:px-8 selection:bg-blue-100 selection:text-blue-900 font-sans">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        {/* Logo and Header */}
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-600 text-white shadow-sm mb-4">
          <Scale className="w-6 h-6" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-[#0F172A]">
          Metrolab NAWI Platform
        </h2>
        <p className="mt-1 text-xs text-[#64748B]">
          Digital Verification &amp; Certification System · OIML R-76
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-lg px-4 sm:px-0">
        <div className="bg-white py-8 px-6 shadow-sm border border-[#E2E8F0] rounded-xl sm:px-10">
          {/* Quick Role Autofill Selectors */}
          <div className="mb-6">
            <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2">
              Select Role Autofill Credentials:
            </label>
            <div className="grid grid-cols-2 gap-2">
              {PRESET_ROLES.map((preset) => {
                const Icon = preset.icon;
                const isSelected =
                  username === preset.username &&
                  selectedRole.role === preset.role;
                return (
                  <button
                    key={preset.role}
                    type="button"
                    onClick={() => handleSelectPreset(preset)}
                    className={`flex flex-col text-left p-2.5 rounded-lg border transition-all text-xs ${
                      isSelected
                        ? "border-blue-500 bg-blue-50/40 ring-1 ring-blue-500"
                        : "border-[#E2E8F0] bg-white hover:bg-slate-50 text-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between w-full mb-1">
                      <div className="flex items-center space-x-1.5 font-semibold text-slate-900">
                        <Icon className="w-3.5 h-3.5 text-blue-600" />
                        <span>{preset.label}</span>
                      </div>
                      {isSelected && (
                        <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
                      )}
                    </div>
                    <span className="text-[11px] text-slate-500 truncate">
                      {preset.username}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Error Banner */}
          {errorMessage && (
            <div className="mb-5 p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-start space-x-2.5 text-xs text-rose-700 animate-in fade-in">
              <AlertCircle className="w-4 h-4 text-rose-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1 font-medium">{errorMessage}</div>
            </div>
          )}

          {/* Real Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="username"
                className="block text-xs font-semibold text-slate-700 mb-1"
              >
                Username
              </label>
              <div className="relative rounded-md shadow-xs">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <User className="h-4 w-4" />
                </div>
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  value={username}
                  onChange={(e) => {
                    setUsername(e.target.value);
                    setErrorMessage(null);
                  }}
                  className="block w-full pl-9 pr-3 py-2 text-xs border border-[#E2E8F0] rounded-lg bg-[#F8FAFC] text-[#0F172A] placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-colors font-mono"
                  placeholder="Enter username"
                  autoComplete="username"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-xs font-semibold text-slate-700 mb-1"
              >
                Password
              </label>
              <div className="relative rounded-md shadow-xs">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    setErrorMessage(null);
                  }}
                  className="block w-full pl-9 pr-10 py-2 text-xs border border-[#E2E8F0] rounded-lg bg-[#F8FAFC] text-[#0F172A] placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-colors font-mono"
                  placeholder="Enter password"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 focus:outline-none"
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-60 transition-colors cursor-pointer"
              >
                {isLoading ? (
                  <span>Authenticating...</span>
                ) : (
                  <>
                    <span>Sign In to Laboratory System</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Statutory Metrology Notice */}
          <div className="mt-6 pt-5 border-t border-[#E2E8F0] text-center">
            <p className="text-[11px] text-[#64748B]">
              Authorized personnel only. Access is cryptographically signed and
              audited under Legal Metrology Act, 2009.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
