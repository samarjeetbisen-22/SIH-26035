import React, { useState } from 'react';
import { UserCheck, Shield, Award, Building, LogIn, LogOut, Check } from 'lucide-react';
import { UserSession, loginUser, logoutUser } from '../utils/apiClient';

interface AuthRoleSwitcherProps {
  currentUser: UserSession | null;
  onUserChange: (user: UserSession | null) => void;
  onOpenReviewerQueue: () => void;
  onOpenOwnerPortal: () => void;
  onNotification: (msg: string) => void;
}

export const AuthRoleSwitcher: React.FC<AuthRoleSwitcherProps> = ({
  currentUser,
  onUserChange,
  onOpenReviewerQueue,
  onOpenOwnerPortal,
  onNotification,
}) => {
  const [switching, setSwitching] = useState(false);

  const presetRoles = [
    {
      role: 'INSPECTOR',
      label: 'Inspector',
      name: 'Rajesh Kumar',
      org: 'RRSL Metrology Dept',
      username: 'rajesh_inspector',
      pwd: 'Inspector@123',
      icon: Award,
      badgeColor: 'bg-blue-50 text-blue-700 border-blue-200'
    },
    {
      role: 'REVIEWER',
      label: 'Reviewer',
      name: 'Dr. Priya Sharma',
      org: 'NABL Certified Reviewer',
      username: 'priya_reviewer',
      pwd: 'Reviewer@123',
      icon: Shield,
      badgeColor: 'bg-purple-50 text-purple-700 border-purple-200'
    },
    {
      role: 'OWNER',
      label: 'Owner',
      name: 'Essae Digitronics',
      org: 'Essae Fleet Portal',
      username: 'essae_owner',
      pwd: 'Owner@123',
      icon: Building,
      badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200'
    },
    {
      role: 'ADMIN',
      label: 'Admin',
      name: 'S. Roy',
      org: 'Legal Metrology HQ',
      username: 'admin',
      pwd: 'Admin@123',
      icon: UserCheck,
      badgeColor: 'bg-amber-50 text-amber-700 border-amber-200'
    },
  ];

  const handleQuickSwitch = async (rolePreset: typeof presetRoles[0]) => {
    setSwitching(true);
    try {
      const res = await loginUser(rolePreset.username, rolePreset.pwd);
      if (res.success && res.user) {
        onUserChange(res.user);
        onNotification(`Switched role to ${rolePreset.label} (${rolePreset.name})`);
      } else {
        alert(res.error || 'Failed to authenticate');
      }
    } finally {
      setSwitching(false);
    }
  };

  const handleLogout = async () => {
    await logoutUser();
    onUserChange(null);
    onNotification('Logged out successfully');
  };

  return (
    <div className="bg-slate-50 border-b border-[#E2E8F0] px-4 sm:px-6 lg:px-8 py-1.5 text-xs flex flex-wrap items-center justify-between gap-2">
      <div className="flex items-center space-x-2">
        <span className="font-semibold text-slate-500 uppercase tracking-wider text-[10px]">Active Role Switcher:</span>
        <div className="flex items-center space-x-1.5">
          {presetRoles.map((p) => {
            const isActive = currentUser?.role === p.role;
            const Icon = p.icon;
            return (
              <button
                key={p.role}
                onClick={() => handleQuickSwitch(p)}
                disabled={switching}
                className={`flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-medium border transition-all ${
                  isActive
                    ? 'bg-white text-slate-900 border-slate-300 shadow-xs ring-1 ring-blue-500/20 font-semibold'
                    : 'bg-transparent text-slate-600 border-transparent hover:bg-white/60 hover:text-slate-900'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-blue-600' : 'text-slate-400'}`} />
                <span>{p.label}</span>
                {isActive && <Check className="w-3 h-3 text-blue-600 ml-0.5" />}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex items-center space-x-3">
        {/* Role Specific Actions */}
        {(currentUser?.role === 'REVIEWER' || currentUser?.role === 'ADMIN') && (
          <button
            onClick={onOpenReviewerQueue}
            className="flex items-center space-x-1 px-2.5 py-0.5 rounded text-[11px] font-medium bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100 transition-colors"
          >
            <Shield className="w-3 h-3" />
            <span>Open Reviewer Queue</span>
          </button>
        )}

        {(currentUser?.role === 'OWNER' || currentUser?.role === 'ADMIN') && (
          <button
            onClick={onOpenOwnerPortal}
            className="flex items-center space-x-1 px-2.5 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 transition-colors"
          >
            <Building className="w-3 h-3" />
            <span>Open Owner Fleet Portal</span>
          </button>
        )}

        {/* Current User Session Info */}
        {currentUser ? (
          <div className="flex items-center space-x-2 pl-2 border-l border-slate-200">
            <span className="text-slate-500 font-mono text-[11px]">
              {currentUser.full_name} ({currentUser.role})
            </span>
            <button
              onClick={handleLogout}
              title="Logout"
              className="p-1 text-slate-400 hover:text-rose-600 transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <button
            onClick={() => handleQuickSwitch(presetRoles[0])}
            className="flex items-center space-x-1 text-blue-600 hover:text-blue-800"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Sign In</span>
          </button>
        )}
      </div>
    </div>
  );
};
