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

import { httpResource, HttpResourceRef } from "@angular/common/http";
import { Component, computed, inject, input, SecurityContext } from "@angular/core";
import { DomSanitizer } from "@angular/platform-browser";
import { EnrollmentResponseDetail } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { environment } from "@env/environment";
import { StringUtils } from "@utils/string.utils";

// TODO: Get custom path from pi.cfg
const CUSTOMIZATION_PATH = "/static/public/customize/";

/**
 * Frames the content of every enrollment step after the enroll click with the wizard's customization,
 * the post top and post bottom HTML. Without `enabled` it only shows its content.
 */
@Component({
  selector: "app-enrollment-customization-frame",
  templateUrl: "./enrollment-customization-frame.component.html"
})
export class EnrollmentCustomizationFrameComponent {
  private readonly sanitizer = inject(DomSanitizer);

  enabled = input<boolean>(false);
  enrollmentDetail = input<EnrollmentResponseDetail | undefined>();

  private readonly tagData = computed<Record<string, string>>(() => {
    const detail = this.enrollmentDetail();
    const qrSource = detail?.googleurl ?? detail?.pushurl ?? detail?.motpurl ?? detail?.otpkey ?? detail?.tiqrenroll;
    return {
      serial: detail?.serial ?? "",
      qrCode: qrSource?.img ?? "",
      url: qrSource?.value ?? ""
    };
  });

  private readonly postTop = this.customization("token-enrollment.wizard.post.top.html");
  private readonly postBottom = this.customization("token-enrollment.wizard.post.bottom.html");

  protected readonly postTopHtml = computed(() => this.render(this.postTop));
  protected readonly postBottomHtml = computed(() => this.render(this.postBottom));

  private customization(fileName: string): HttpResourceRef<string | undefined> {
    return httpResource.text(() => (this.enabled() ? environment.proxyUrl + CUSTOMIZATION_PATH + fileName : undefined));
  }

  private render(resource: HttpResourceRef<string | undefined>): string | null {
    const raw = resource.hasValue() ? (resource.value() ?? "") : "";
    if (!raw.trim()) {
      return null;
    }
    return this.sanitizer.sanitize(SecurityContext.HTML, StringUtils.replaceWithTags(raw, this.tagData()));
  }
}
