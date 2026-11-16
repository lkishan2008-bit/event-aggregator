"use client";

import Link from "next/link";
import { useSession } from "@/lib/auth";

/** Top-right of the home screen: "Log in" when logged out, the user's first name when logged in. */
export default function UserBadge() {
    const session = useSession();
    if (!session) {
        return <Link href="/login" className="rounded-full bg-ink px-3 py-1 text-xs font-medium text-white">Log in</Link>;
    }
    return (
        <Link href="/profile" className="rounded-full bg-ink px-3 py-1 text-xs font-medium text-white">
            Hi, {session.user.name.split(" ")[0]}
        </Link>
    );
}