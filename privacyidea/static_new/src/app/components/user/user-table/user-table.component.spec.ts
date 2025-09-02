import { ComponentFixture, TestBed } from "@angular/core/testing";

import { UserTableComponent } from "./user-table.component";
import { provideHttpClient } from "@angular/common/http";

describe("UserTableComponent", () => {
  let component: UserTableComponent;
  let fixture: ComponentFixture<UserTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [provideHttpClient()],
      imports: [UserTableComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(UserTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
