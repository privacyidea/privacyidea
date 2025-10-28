/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { ActivatedRoute } from "@angular/router";
import { of } from "rxjs";
import { AuditService } from "../../../services/audit/audit.service";
import { UserService } from "../../../services/user/user.service";
import { UserCardComponent } from "./user-card.component";
import { MockAuditService, MockUserService } from "../../../../testing/mock-services";

describe("UserCardComponent", () => {
  let component: UserCardComponent;
  let fixture: ComponentFixture<UserCardComponent>;
  let auditService: MockAuditService;
  let userService: MockUserService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({ id: "123" })
          }
        },
        { provide: AuditService, useClass: MockAuditService },
        { provide: UserService, useClass: MockUserService },


        provideHttpClient(),
        provideHttpClientTesting()
      ],
      imports: [UserCardComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(UserCardComponent);
    component = fixture.componentInstance;

    auditService = TestBed.inject(AuditService) as unknown as MockAuditService;
    userService = TestBed.inject(UserService) as unknown as MockUserService;

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("showUserAuditLog should set the audit filter to the current username", () => {
    const username = "alice";
    userService.detailsUsername.set(username);

    component.showUserAuditLog();

    const filter = auditService.auditFilter();
    expect(filter).toBeTruthy();
    expect(filter.value).toBe(`user: ${username}`);
  });
});
