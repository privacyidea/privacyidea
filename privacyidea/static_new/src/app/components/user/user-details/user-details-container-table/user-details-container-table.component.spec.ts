import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UserDetailsContainerTableComponent } from './user-details-container-table.component';

describe('UserDetailsContainerTableComponent', () => {
  let component: UserDetailsContainerTableComponent;
  let fixture: ComponentFixture<UserDetailsContainerTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserDetailsContainerTableComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(UserDetailsContainerTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
