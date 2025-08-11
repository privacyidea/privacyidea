import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UserComponent } from './user.component';
import { provideHttpClient } from '@angular/common/http';
import { signal } from '@angular/core';
import { UserData, UserService } from '../../services/user/user.service';

class MockUserService {
  user = signal<UserData>({
    description: '',
    editable: false,
    email: '',
    givenname: '',
    mobile: '',
    phone: '',
    resolver: '',
    surname: '',
    userid: '',
    username: 'test',
  });
}

describe('UserComponent', () => {
  let component: UserComponent;
  let fixture: ComponentFixture<UserComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        { provide: UserService, useClass: MockUserService },
      ],
      imports: [UserComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(UserComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
