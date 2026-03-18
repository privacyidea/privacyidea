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

import { UserTableComponent } from "./user-table.component";
import { provideHttpClient } from "@angular/common/http";
import { ActivatedRoute } from "@angular/router";
import { of } from "rxjs";
import { UserService } from "../../../services/user/user.service";
import { TableUtilsService } from "../../../services/table-utils/table-utils.service";
import { ContentService } from "../../../services/content/content.service";
import {
  MockUserService,
  MockTableUtilsService,
  MockContentService,
  MockLocalService,
  MockNotificationService
} from "../../../../testing/mock-services";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";

describe("UserTableComponent", () => {
  let component: UserTableComponent;
  let fixture: ComponentFixture<UserTableComponent>;
  let mockUserService: MockUserService;
  let mockTableUtilsService: MockTableUtilsService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({ id: "123" })
          }
        },
        { provide: UserService, useClass: MockUserService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: ContentService, useClass: MockContentService },
        MockLocalService,
        MockNotificationService
      ],
      imports: [UserTableComponent, NoopAnimationsModule]
    }).compileComponents();

    fixture = TestBed.createComponent(UserTableComponent);
    component = fixture.componentInstance;
    mockUserService = TestBed.inject(UserService) as unknown as MockUserService;
    mockTableUtilsService = TestBed.inject(TableUtilsService) as unknown as MockTableUtilsService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("pageSizeOptions should add custom page size if not included in default options", () => {
    const defaultOptions = [5, 10, 25, 50];
    mockTableUtilsService.pageSizeOptions.set(defaultOptions);
    expect(component.pageSizeOptions()).toEqual(defaultOptions);

    // Check custom page size is added but does not mutate the options from the service
    const customOptions = [5, 10, 15, 25, 50];
    mockUserService.pageSize.set(15);
    expect(component.pageSizeOptions()).toEqual(customOptions);
    expect(mockTableUtilsService.pageSizeOptions()).toEqual(defaultOptions);

    // custom page size should still be included if selected pageSize changes
    mockUserService.pageSize.set(10);
    expect(component.pageSizeOptions()).toEqual(customOptions);
  });
});
