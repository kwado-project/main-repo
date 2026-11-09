/** @type {import('next').NextConfig} */
const BACKEND = process.env.BACKEND_URL || "http://127.0.0.1:8000";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Same-origin API: the refresh cookie stays first-party and httpOnly.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND}/api/:path*/` }];
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  skipTrailingSlashRedirect: true,
};

export default nextConfig;
