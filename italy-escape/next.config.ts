import type { NextConfig } from "next";

/** Hotel photography is served from each property's own CDN or its Booking.com listing. */
const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "cf.bstatic.com" },
      { protocol: "https", hostname: "img.belmond.com" },
      { protocol: "https", hostname: "images.rosewoodhotels.com" },
      { protocol: "https", hostname: "cdn.blastness.biz" },
      { protocol: "https", hostname: "de87ve0y4m3tc.cloudfront.net" },
      { protocol: "https", hostname: "www.hotelpiccada.com" },
      { protocol: "https", hostname: "www.villalebarone.com" },
    ],
  },
};

export default nextConfig;
