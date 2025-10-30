import { ComponentFixture, TestBed } from "@angular/core/testing";

import { UserTableActionsComponent } from "./user-table-actions.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ActivatedRoute } from "@angular/router";
import { of } from "rxjs";

describe("UserTableActionsComponent", () => {
  let component: UserTableActionsComponent;
  let fixture: ComponentFixture<UserTableActionsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({ id: "123" })
          }
        }],
      imports: [UserTableActionsComponent]
    })
      .compileComponents();

    fixture = TestBed.createComponent(UserTableActionsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
