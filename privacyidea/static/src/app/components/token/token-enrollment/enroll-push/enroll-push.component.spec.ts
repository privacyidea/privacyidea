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
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { PushApiPayloadMapper } from "@app/mappers/token-api-payload/push-token-api-payload.mapper";
import { EnrollTokenBase } from "@components/token/token-enrollment/enroll-token-base";
import { TokenService } from "@services/token/token.service";
import { MockTokenService } from "@testing/mock-services";
import { EnrollPushComponent } from "./enroll-push.component";
import { axe } from "@testing/axe";

class DummyPushApiPayloadMapper {
  map<T>(x: T): T {
    return x;
  }
}

describe("EnrollPushComponent", () => {
  let fixture: ComponentFixture<EnrollPushComponent>;
  let component: EnrollPushComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollPushComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: PushApiPayloadMapper, useClass: DummyPushApiPayloadMapper }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollPushComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("does not show the enrollment data in the last step dialog", () => {
    expect(component.showEnrollDataInLastStep).toBe(false);
  });

  it("buildEnrollmentArgs returns a push-typed payload bound to the push mapper", () => {
    const args = component.buildEnrollmentArgs({ type: "push", realm: "r", username: "u" });
    expect(args).not.toBeNull();
    expect(args!.data.type).toBe("push");
    expect(args!.mapper).toBe(TestBed.inject(PushApiPayloadMapper));
  });

  it("hands the enrollment dialog the push step, which polls until the app registered the token", () => {
    expect(component.firstStep()).toEqual({ kind: "push" });
  });

  it("provides itself as EnrollTokenBase", () => {
    expect(fixture.debugElement.injector.get(EnrollTokenBase)).toBe(component);
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
