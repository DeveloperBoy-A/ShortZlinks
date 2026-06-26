import mongoose, { Schema, model, models } from "mongoose";

/* =========================================================
   USER
========================================================= */

const UserSchema = new Schema(
  {
    username: {
      type: String,
      unique: true,
      required: true,
      trim: true
    },

    email: {
      type: String,
      unique: true,
      required: true,
      lowercase: true
    },

    password: {
      type: String,
      required: true
    },

    role: {
      type: String,
      enum: ["member", "admin", "staff"],
      default: "member"
    },

    avatar: {
      type: String,
      default: ""
    },

    bio: {
      type: String,
      default: ""
    },

    country: {
      type: String,
      default: ""
    },

    timezone: {
      type: String,
      default: "Asia/Kolkata"
    },

    language: {
      type: String,
      default: "en"
    },

    apiKey: {
      type: String,
      default: ""
    },

    apiEnabled: {
      type: Boolean,
      default: true
    },

    telegramId: {
      type: String,
      default: ""
    },

    telegramUsername: {
      type: String,
      default: ""
    },

    botConnected: {
      type: Boolean,
      default: false
    },

    emailVerified: {
      type: Boolean,
      default: false
    },

    twoFAEnabled: {
      type: Boolean,
      default: false
    },

    banned: {
      type: Boolean,
      default: false
    },

    active: {
      type: Boolean,
      default: true
    },

    referralCode: {
      type: String,
      default: ""
    },

    referredBy: {
      type: Schema.Types.ObjectId,
      ref: "User",
      default: null
    },

    walletBalance: {
      type: Number,
      default: 0
    },

    referralBalance: {
      type: Number,
      default: 0
    },

    totalViews: {
      type: Number,
      default: 0
    },

    totalLinks: {
      type: Number,
      default: 0
    },

    totalEarned: {
      type: Number,
      default: 0
    },

    totalWithdrawn: {
      type: Number,
      default: 0
    },

    loginIP: {
      type: String,
      default: ""
    },

    lastLogin: Date,

    sessionExpires: Date,

sessionId: {
  type: String,
  default: ""
}
  },
  {
    timestamps: true
  }
);

/* =========================================================
   LINK
========================================================= */

const LinkSchema = new Schema(
  {
    owner: {
      type: Schema.Types.ObjectId,
      ref: "User",
      required: true
    },

    title: {
      type: String,
      default: ""
    },

    alias: {
      type: String,
      unique: true,
      required: true
    },

    destination: {
      type: String,
      required: true
    },

    qrCode: {
      type: String,
      default: ""
    },

    password: {
      type: String,
      default: ""
    },

    expiresAt: Date,

    hidden: {
      type: Boolean,
      default: false
    },

    active: {
      type: Boolean,
      default: true
    },

    routeSteps: {
      type: Number,
      default: 2
    },

    views: {
      type: Number,
      default: 0
    },

    earnings: {
      type: Number,
      default: 0
    },

    referralEarnings: {
      type: Number,
      default: 0
    },

    averageCPM: {
      type: Number,
      default: 0
    },

    lastVisit: Date
  },
  {
    timestamps: true
  }
);

/* =========================================================
   CLICK
========================================================= */

const ClickSchema = new Schema(
  {
    link: {
      type: Schema.Types.ObjectId,
      ref: "Link"
    },

    owner: {
      type: Schema.Types.ObjectId,
      ref: "User"
    },

    ip: String,

    country: String,

    countryCode: String,

    city: String,

    device: String,

    browser: String,

    os: String,

    referer: String,

    proxy: {
      type: Boolean,
      default: false
    },

    vpn: {
      type: Boolean,
      default: false
    },

    unique: {
      type: Boolean,
      default: true
    },

    revenue: {
      type: Number,
      default: 0
    }
  },
  {
    timestamps: true
  }
);

export const User =
  models.User || model("User", UserSchema);

export const Link =
  models.Link || model("Link", LinkSchema);

export const Click =
  models.Click || model("Click", ClickSchema);

/* =========================================================
   WALLET
========================================================= */

const WalletSchema = new Schema(
  {
    user: {
      type: Schema.Types.ObjectId,
      ref: "User",
      required: true,
      unique: true
    },

    balance: {
      type: Number,
      default: 0
    },

    referralBalance: {
      type: Number,
      default: 0
    },

    pendingBalance: {
      type: Number,
      default: 0
    },

    totalEarned: {
      type: Number,
      default: 0
    },

    totalWithdrawn: {
      type: Number,
      default: 0
    },

    lifetimeReferral: {
      type: Number,
      default: 0
    }
  },
  {
    timestamps: true
  }
);

/* =========================================================
   WITHDRAWAL
========================================================= */

const WithdrawalSchema = new Schema(
  {
    user: {
      type: Schema.Types.ObjectId,
      ref: "User",
      required: true
    },

    amount: {
      type: Number,
      required: true
    },

    method: {
      type: String,
      enum: ["UPI", "PayPal", "Bank", "Crypto"],
      required: true
    },

    accountName: String,
    accountNumber: String,
    ifsc: String,
    upiId: String,
    walletAddress: String,

    trafficSource: String,
    submittedLink: String,

    status: {
      type: String,
      enum: ["Pending", "Approved", "Rejected", "Completed"],
      default: "Pending"
    },

    adminRemark: {
      type: String,
      default: ""
    },

    approvedBy: {
      type: Schema.Types.ObjectId,
      ref: "User"
    },

    approvedAt: Date,

    completedAt: Date
  },
  {
    timestamps: true
  }
);

/* =========================================================
   PAYMENT HISTORY
========================================================= */

const PaymentSchema = new Schema(
  {
    user: {
      type: Schema.Types.ObjectId,
      ref: "User"
    },

    withdrawal: {
      type: Schema.Types.ObjectId,
      ref: "Withdrawal"
    },

    amount: Number,

    method: String,

    transactionId: String,

    status: {
      type: String,
      default: "Pending"
    }
  },
  {
    timestamps: true
  }
);

/* =========================================================
   REFERRAL
========================================================= */

const ReferralSchema = new Schema(
  {
    inviter: {
      type: Schema.Types.ObjectId,
      ref: "User"
    },

    invited: {
      type: Schema.Types.ObjectId,
      ref: "User"
    },

    commissionRate: {
      type: Number,
      default: 10
    },

    totalCommission: {
      type: Number,
      default: 0
    },

    active: {
      type: Boolean,
      default: true
    }
  },
  {
    timestamps: true
  }
);

/* =========================================================
   NOTIFICATIONS
========================================================= */

const NotificationSchema = new Schema(
  {
    user: {
      type: Schema.Types.ObjectId,
      ref: "User"
    },

    title: String,

    message: String,

    icon: {
      type: String,
      default: "bell"
    },

    read: {
      type: Boolean,
      default: false
    },

    type: {
      type: String,
      default: "info"
    }
  },

    details: {
  type: Schema.Types.Mixed,
  default: {}
},
  {
    timestamps: true
  }
);

/* =========================================================
   ANNOUNCEMENTS
========================================================= */

const AnnouncementSchema = new Schema(
  {
    title: {
      type: String,
      required: true
    },

    message: {
      type: String,
      required: true
    },

    active: {
      type: Boolean,
      default: true
    },

    priority: {
      type: Number,
      default: 1
    }
  },
  {
    timestamps: true
  }
);

/* =========================================================
   EXPORTS
========================================================= */

export const Wallet =
  models.Wallet || model("Wallet", WalletSchema);

export const Withdrawal =
  models.Withdrawal ||
  model("Withdrawal", WithdrawalSchema);

export const Payment =
  models.Payment ||
  model("Payment", PaymentSchema);

export const Referral =
  models.Referral ||
  model("Referral", ReferralSchema);

export const Notification =
  models.Notification ||
  model("Notification", NotificationSchema);

export const Announcement =
  models.Announcement ||
  model("Announcement", AnnouncementSchema);

/* =========================================================
   SUPPORT TICKET
========================================================= */

const TicketSchema = new Schema(
  {
    user: {
      type: Schema.Types.ObjectId,
      ref: "User",
      required: true
    },

    subject: {
      type: String,
      required: true
    },

    message: {
      type: String,
      required: true
    },

    category: {
      type: String,
      default: "General"
    },

    priority: {
      type: String,
      enum: ["Low", "Medium", "High"],
      default: "Medium"
    },

    status: {
      type: String,
      enum: ["Open", "Pending", "Closed"],
      default: "Open"
    },

    adminReply: {
      type: String,
      default: ""
    }
  },
  {
    timestamps: true
  }
);

/* =========================================================
   PROMO CODE
========================================================= */

const PromoSchema = new Schema(
  {
    code: {
      type: String,
      unique: true,
      required: true
    },

    reward: {
      type: Number,
      default: 0
    },

    maxUses: {
      type: Number,
      default: 100
    },

    usedCount: {
      type: Number,
      default: 0
    },

    expiresAt: Date,

    active: {
      type: Boolean,
      default: true
    }
  },
  {
    timestamps: true
  }
);

/* =========================================================
   API KEY
========================================================= */

const ApiKeySchema = new Schema(
  {
    user: {
      type: Schema.Types.ObjectId,
      ref: "User"
    },

    key: {
      type: String,
      unique: true,
      required: true
    },

    requestsToday: {
      type: Number,
      default: 0
    },

    lastRequest: Date,

    blocked: {
      type: Boolean,
      default: false
    },

    lastUsedIP: {
  type: String,
  default: ""
},

lastUsedAt: Date,

    whitelistIPs: [
      {
        type: String
      }
    ]
  },
  {
    timestamps: true
  }
);

/* =========================================================
   TRAFFIC LOG
========================================================= */

const TrafficLogSchema = new Schema(
  {
    user: {
      type: Schema.Types.ObjectId,
      ref: "User"
    },

    link: {
      type: Schema.Types.ObjectId,
      ref: "Link"
    },

    ip: String,

    country: String,

    browser: String,

    device: String,

    os: String,

    revenue: {
      type: Number,
      default: 0
    },

    valid: {
      type: Boolean,
      default: true
    }
  },
  {
    timestamps: true
  }
);

/* =========================================================
   AUDIT LOG
========================================================= */

const AuditLogSchema = new Schema(
  {
    admin: {
      type: Schema.Types.ObjectId,
      ref: "User"
    },

    action: String,

    target: String,

    details: {
  type: Schema.Types.Mixed,
  default: {}
},

    ip: String
  },
  {
    timestamps: true
  }
);

/* =========================================================
   ABUSE REPORT
========================================================= */

const AbuseSchema = new Schema(
  {
    reporterEmail: String,

    alias: String,

    reason: String,

    status: {
      type: String,
      default: "Pending"
    }
  },
  {
    timestamps: true
  }
);

/* =========================================================
   SITE SETTINGS
========================================================= */

const SiteSettingSchema = new Schema(
  {
    siteName: String,

    siteDomain: String,

    maintenance: {
      type: Boolean,
      default: false
    },

    announcement: String,

    referralPercent: {
      type: Number,
      default: 10
    },

    autoCPM: {
      type: Boolean,
      default: true
    },

    withdrawalEnabled: {
      type: Boolean,
      default: true
    }
  },
    botEnabled: {
  type: Boolean,
  default: false
},

defaultRouteSteps: {
  type: Number,
  default: 2
},

defaultStep1Timer: {
  type: Number,
  default: 15
},

defaultStep2Timer: {
  type: Number,
  default: 10
},

defaultStep3Timer: {
  type: Number,
  default: 10
},
  {
    timestamps: true
  }
);

/* =========================================================
   AD TEMPLATE
========================================================= */

const AdTemplateSchema = new Schema(
  {
    title: String,

    category: String,

    html: String,

    active: {
      type: Boolean,
      default: true
    }
  },
  {
    timestamps: true
  }
);

/* =========================================================
   DOMAIN
========================================================= */

const DomainSchema = new Schema(
  {
    domain: {
      type: String,
      unique: true
    },

    primary: {
      type: Boolean,
      default: false
    },

    active: {
      type: Boolean,
      default: true
    }
  },
  {
    timestamps: true
  }
);

/* =========================================================
   EXPORTS
========================================================= */

export const Ticket =
  models.Ticket || model("Ticket", TicketSchema);

export const Promo =
  models.Promo || model("Promo", PromoSchema);

export const ApiKey =
  models.ApiKey || model("ApiKey", ApiKeySchema);

export const TrafficLog =
  models.TrafficLog || model("TrafficLog", TrafficLogSchema);

export const AuditLog =
  models.AuditLog || model("AuditLog", AuditLogSchema);

export const AbuseReport =
  models.AbuseReport || model("AbuseReport", AbuseSchema);

export const SiteSetting =
  models.SiteSetting || model("SiteSetting", SiteSettingSchema);

export const AdTemplate =
  models.AdTemplate || model("AdTemplate", AdTemplateSchema);

export const Domain =
  models.Domain || model("Domain", DomainSchema);