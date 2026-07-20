/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

import { HttpClient, HttpErrorResponse, httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, effect, inject, Injectable, Signal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { lastValueFrom } from "rxjs";

// Mirrors privacyidea.lib.conditional_access.authentication_error_codes.AuthEventType
export type AuthEventType =
  | "NOT_AUTHORIZED"
  | "PASSWORD_FAIL"
  | "PIN_FAIL"
  | "TOKEN_ONLY_FAIL"
  | "MFA_FAIL"
  | "USER_UNKNOWN"
  | "NO_TOKEN"
  | "NO_USABLE_TOKEN"
  | "LOGIN_SUCCESS"
  | "CHALLENGE_CONTINUED"
  | "CHALLENGE_TRIGGERED"
  | "CHALLENGE_ANSWERED_OUT_OF_BAND"
  | "CHALLENGE_ANSWERED_FAIL"
  | "CHALLENGE_DECLINED"
  | "ENROLLMENT_TRIGGERED"
  | "ENROLLMENT_CANCELED_FAIL"
  | "UNKNOWN_FAIL_REASON";

export const ALL_AUTH_EVENT_TYPES: AuthEventType[] = [
  "NOT_AUTHORIZED",
  "PASSWORD_FAIL",
  "PIN_FAIL",
  "TOKEN_ONLY_FAIL",
  "MFA_FAIL",
  "USER_UNKNOWN",
  "NO_TOKEN",
  "NO_USABLE_TOKEN",
  "LOGIN_SUCCESS",
  "CHALLENGE_CONTINUED",
  "CHALLENGE_TRIGGERED",
  "CHALLENGE_ANSWERED_OUT_OF_BAND",
  "CHALLENGE_ANSWERED_FAIL",
  "CHALLENGE_DECLINED",
  "ENROLLMENT_TRIGGERED",
  "ENROLLMENT_CANCELED_FAIL",
  "UNKNOWN_FAIL_REASON"
];

// Mirrors privacyidea.lib.conditional_access.engine.LockoutAction
export type LockoutActionType =
  | "LOCK_USER"
  | "PERMANENT_LOCK_USER"
  | "EMAIL_ADMIN"
  | "EMAIL_USER"
  | "BLOCK_IP"
  | "PERMANENT_BLOCK_IP"
  | "ALLOW"
  | "DENY";

export const ALL_LOCKOUT_ACTIONS: LockoutActionType[] = [
  "LOCK_USER",
  "PERMANENT_LOCK_USER",
  "EMAIL_ADMIN",
  "EMAIL_USER",
  "BLOCK_IP",
  "PERMANENT_BLOCK_IP",
  "ALLOW",
  "DENY"
];

export interface LockoutStageAction {
  id?: number;
  action_type: LockoutActionType;
  action_value: unknown;
}

export interface LockoutPolicyStage {
  id?: number;
  failure_threshold: number;
  priority: number;
  actions: LockoutStageAction[];
}

export interface LockoutPolicy {
  id: number;
  name: string;
  time_window_seconds: number;
  enabled: boolean;
  dry_run: boolean;
  priority: number;
  counter_types_to_track: AuthEventType[];
  stages: LockoutPolicyStage[];
}

// The shape sent to create/update; id is only present (and ignored server-side) on update.
export type LockoutPolicySaveParams = Omit<LockoutPolicy, "id"> & { id?: number };

export const EMPTY_LOCKOUT_POLICY: LockoutPolicySaveParams = {
  name: "",
  time_window_seconds: 600,
  enabled: true,
  dry_run: false,
  priority: 1,
  counter_types_to_track: [],
  stages: []
};

export interface ConditionalAccessPolicyServiceInterface {
  readonly policiesResource: HttpResourceRef<PiResponse<LockoutPolicy[]> | undefined>;
  readonly policies: Signal<LockoutPolicy[]>;

  savePolicy(policy: LockoutPolicySaveParams): Promise<number | undefined>;

  deletePolicy(id: number): Promise<void>;

  deleteWithConfirmDialog(policy: { id: number; name: string }): Promise<void>;

  deleteSelectedWithConfirmDialog(policies: { id: number; name: string }[]): Promise<boolean>;

  enablePolicy(id: number): Promise<void>;

  disablePolicy(id: number): Promise<void>;
}

@Injectable()
export class ConditionalAccessPolicyService implements ConditionalAccessPolicyServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http = inject(HttpClient);

  readonly baseUrl = environment.proxyUrl + "/conditionalaccess/policy";

  readonly policiesResource = httpResource<PiResponse<LockoutPolicy[]>>(() => {
    if (!this.authService.actionAllowed("conditional_access_read")) {
      return undefined;
    }
    if (!this.contentService.onConditionalAccess()) {
      return undefined;
    }
    return {
      url: this.baseUrl,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  readonly policies: Signal<LockoutPolicy[]> = computed(() => {
    if (this.policiesResource.hasValue()) {
      return this.policiesResource.value()?.result?.value ?? [];
    }
    return [];
  });

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.policiesResource.error(), "conditional-access policies");
    });
  }

  async savePolicy(policy: LockoutPolicySaveParams): Promise<number | undefined> {
    const headers = this.authService.getHeaders();
    const isUpdate = policy.id != null;
    const request = isUpdate
      ? this.http.patch<PiResponse<number>>(`${this.baseUrl}/${policy.id}`, policy, { headers })
      : this.http.post<PiResponse<number>>(this.baseUrl, policy, { headers });

    try {
      const response = await lastValueFrom(request);
      this.notificationService.success(
        isUpdate
          ? $localize`Successfully updated conditional-access policy.`
          : $localize`Successfully created conditional-access policy.`
      );
      this.policiesResource.reload();
      return response?.result?.value;
    } catch (error) {
      const httpError = error as HttpErrorResponse;
      const body = httpError.error as PiResponse<number> | undefined;
      const message = body?.result?.error?.message || "";
      this.notificationService.error($localize`Failed to save conditional-access policy. ` + message);
      return undefined;
    }
  }

  async deletePolicy(id: number): Promise<void> {
    const headers = this.authService.getHeaders();
    const request = this.http.delete<PiResponse<number>>(`${this.baseUrl}/${id}`, { headers });

    try {
      await lastValueFrom(request);
      this.notificationService.success($localize`Successfully deleted conditional-access policy.`);
      this.policiesResource.reload();
    } catch (error) {
      const httpError = error as HttpErrorResponse;
      const body = httpError.error as PiResponse<number> | undefined;
      const message = body?.result?.error?.message || "";
      this.notificationService.error($localize`Failed to delete conditional-access policy. ` + message);
    }
  }

  async deleteWithConfirmDialog(policy: { id: number; name: string }): Promise<void> {
    const confirmed = await this.dialogService.confirm({
      title: $localize`Delete Conditional-Access Policy`,
      message: $localize`Do you really want to delete the policy "${policy.name}"?`,
      confirmButtonText: $localize`Delete`
    });
    if (!confirmed) {
      return;
    }
    await this.deletePolicy(policy.id);
  }

  async deleteSelectedWithConfirmDialog(policies: { id: number; name: string }[]): Promise<boolean> {
    if (policies.length === 0) {
      return false;
    }
    const confirmed = await this.dialogService.confirm({
      title: $localize`Delete Conditional-Access Policies`,
      message: $localize`Do you really want to delete ${policies.length} selected policies?`,
      confirmButtonText: $localize`Delete`
    });
    if (!confirmed) {
      return false;
    }
    const headers = this.authService.getHeaders();
    try {
      await Promise.all(
        policies.map((policy) =>
          lastValueFrom(this.http.delete<PiResponse<number>>(`${this.baseUrl}/${policy.id}`, { headers }))
        )
      );
      this.notificationService.success($localize`Successfully deleted ${policies.length} conditional-access policies.`);
      this.policiesResource.reload();
      return true;
    } catch (error) {
      const httpError = error as HttpErrorResponse;
      const body = httpError.error as PiResponse<number> | undefined;
      const message = body?.result?.error?.message || "";
      this.notificationService.error($localize`Failed to delete conditional-access policies. ` + message);
      this.policiesResource.reload();
      return false;
    }
  }

  async enablePolicy(id: number): Promise<void> {
    const headers = this.authService.getHeaders();
    try {
      await lastValueFrom(this.http.patch(`${this.baseUrl}/${id}`, { enabled: true }, { headers }));
      this.policiesResource.reload();
    } catch {
      this.notificationService.error($localize`Failed to enable conditional-access policy.`);
      this.policiesResource.reload();
    }
  }

  async disablePolicy(id: number): Promise<void> {
    const headers = this.authService.getHeaders();
    try {
      await lastValueFrom(this.http.patch(`${this.baseUrl}/${id}`, { enabled: false }, { headers }));
      this.policiesResource.reload();
    } catch {
      this.notificationService.error($localize`Failed to disable conditional-access policy.`);
      this.policiesResource.reload();
    }
  }
}
