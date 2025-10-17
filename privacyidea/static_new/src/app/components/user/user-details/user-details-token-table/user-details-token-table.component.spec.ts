import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UserDetailsTokenTableComponent } from './user-details-token-table.component';

describe('UserDetailsTokenTableComponent', () => {
  let component: UserDetailsTokenTableComponent;
  let fixture: ComponentFixture<UserDetailsTokenTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserDetailsTokenTableComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(UserDetailsTokenTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
