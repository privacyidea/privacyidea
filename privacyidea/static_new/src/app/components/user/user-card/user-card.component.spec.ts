import { ComponentFixture, TestBed } from "@angular/core/testing";

import { UserCardComponent } from "./user-card.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ActivatedRoute } from "@angular/router";
import { of } from "rxjs";

describe("UserCardComponent", () => {
  let component: UserCardComponent;
  let fixture: ComponentFixture<UserCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({ id: "123" })
          }
        },
        provideHttpClient(),
        provideHttpClientTesting()],
      imports: [UserCardComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(UserCardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
